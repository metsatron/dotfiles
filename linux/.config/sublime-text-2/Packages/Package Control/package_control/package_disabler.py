import json

import sublime

from .settings import preferences_filename, pc_settings_filename, load_list_setting, save_list_setting
from .package_io import package_file_exists, read_package_file
from . import text

# This has to be imported this way for consistency with the public API,
# otherwise this code and packages will each load a different instance of the
# module, and the event tracking won't work. However, upon initial install,
# when running ST3, the module will not yet be imported, and the cwd will not
# be Packages/Package Control/ so we need to patch it into sys.modules.
try:
    from package_control import events
except (ImportError):
    events = None


class PackageDisabler():
    old_color_scheme_package = None
    old_color_scheme = None

    old_theme_package = None
    old_theme = None

    old_syntaxes = None

    def get_version(self, package):
        """
        Gets the current version of a package

        :param package:
            The name of the package

        :return:
            The string version
        """

        if package_file_exists(package, 'package-metadata.json'):
            metadata_json = read_package_file(package, 'package-metadata.json')
            if metadata_json:
                try:
                    return json.loads(metadata_json).get('version', 'unknown version')
                except (ValueError):
                    pass

        return 'unknown version'

    def disable_packages(self, packages, type='upgrade'):
        """
        Disables one or more packages before installing or upgrading to prevent
        errors where Sublime Text tries to read files that no longer exist, or
        read a half-written file.

        :param packages:
            The string package name, or an array of strings

        :param type:
            The type of operation that caused the package to be disabled:
             - "upgrade"
             - "remove"
             - "install"
             - "disable"
             - "loader"

        :return:
            A list of package names that were disabled
        """

        global events

        if events is None:
            from package_control import events

        if not isinstance(packages, list):
            packages = [packages]

        disabled = []

        settings = sublime.load_settings(preferences_filename())
        ignored = load_list_setting(settings, 'ignored_packages')

        pc_settings = sublime.load_settings(pc_settings_filename())
        in_process = load_list_setting(pc_settings, 'in_process_packages')

        self.old_syntaxes = {}
        self.old_color_schemes = {}

        for package in packages:
            if package not in ignored:
                in_process.append(package)
                ignored.append(package)
                disabled.append(package)

            if type in ['upgrade', 'remove']:
                version = self.get_version(package)
                tracker_type = 'pre_upgrade' if type == 'upgrade' else type
                events.add(tracker_type, package, version)

            for window in sublime.windows():
                for view in window.views():
                    view_settings = view.settings()
                    syntax = view_settings.get('syntax')
                    if syntax.find('Packages/' + package + '/') != -1:
                        if package not in self.old_syntaxes:
                            self.old_syntaxes[package] = []
                        self.old_syntaxes[package].append([view, syntax])
                        view_settings.set('syntax', 'Packages/Text/Plain text.tmLanguage')
                    scheme = view_settings.get('color_scheme')
                    if scheme.find('Packages/' + package + '/') != -1:
                        if package not in self.old_color_schemes:
                            self.old_color_schemes[package] = []
                        self.old_color_schemes[package].append([view, scheme])
                        view_settings.set('color_scheme', 'Packages/Color Scheme - Default/Monokai.tmTheme')

            # Change the color scheme before disabling the package containing it
            if settings.get('color_scheme').find('Packages/' + package + '/') != -1:
                self.old_color_scheme_package = package
                self.old_color_scheme = settings.get('color_scheme')
                settings.set('color_scheme', 'Packages/Color Scheme - Default/Monokai.tmTheme')

            # Change the theme before disabling the package containing it
            if package_file_exists(package, settings.get('theme')):
                self.old_theme_package = package
                self.old_theme = settings.get('theme')
                settings.set('theme', 'Default.sublime-theme')

        # We don't mark a package as in-process when disabling it, otherwise
        # it automatically gets re-enabled the next time Sublime Text starts
        if type != 'disable':
            save_list_setting(pc_settings, pc_settings_filename(), 'in_process_packages', in_process)

        save_list_setting(settings, preferences_filename(), 'ignored_packages', ignored)

        return disabled

    def reenable_package(self, package, type='upgrade'):
        """
        Re-enables a package after it has been installed or upgraded

        :param package:
            The string package name

        :param type:
            The type of operation that caused the package to be re-enabled:
             - "upgrade"
             - "remove"
             - "install"
             - "enable"
             - "loader"
        """

        global events

        if events is None:
            from package_control import events

        settings = sublime.load_settings(preferences_filename())
        ignored = load_list_setting(settings, 'ignored_packages')

        if package in ignored:

            if type in ['install', 'upgrade']:
                version = self.get_version(package)
                tracker_type = 'post_upgrade' if type == 'upgrade' else type
                events.add(tracker_type, package, version)
                events.clear(tracker_type, package, future=True)
                if type == 'upgrade':
                    events.clear('pre_upgrade', package)

            elif type == 'remove':
                events.clear('remove', package)

            ignored = list(set(ignored) - set([package]))
            save_list_setting(settings, preferences_filename(), 'ignored_packages', ignored)

            if type == 'remove' and self.old_theme_package == package:
                sublime.message_dialog(text.format(
                    u'''
                    Package Control

                    Your active theme was just removed and the Default theme was
                    enabled in its place. You may see some graphical corruption
                    until you restart Sublime Text.
                    '''
                ))

            # By delaying the restore, we give Sublime Text some time to
            # re-enable the package, making errors less likely
            def delayed_settings_restore():
                if type == 'upgrade' and package in self.old_syntaxes:
                    for view_syntax in self.old_syntaxes[package]:
                        view, syntax = view_syntax
                        view.settings().set('syntax', syntax)

                if type == 'upgrade' and package in self.old_color_schemes:
                    for view_scheme in self.old_color_schemes[package]:
                        view, scheme = view_scheme
                        view.settings().set('color_scheme', scheme)

                if type == 'upgrade' and self.old_theme_package == package:
                    settings.set('theme', self.old_theme)
                    sublime.message_dialog(text.format(
                        u'''
                        Package Control

                        Your active theme was just upgraded. You may see some
                        graphical corruption until you restart Sublime Text.
                        '''
                    ))

                if type == 'upgrade' and self.old_color_scheme_package == package:
                    settings.set('color_scheme', self.old_color_scheme)

                sublime.save_settings(preferences_filename())

            sublime.set_timeout(delayed_settings_restore, 1000)

        pc_settings = sublime.load_settings(pc_settings_filename())
        in_process = load_list_setting(pc_settings, 'in_process_packages')

        if package in in_process:
            in_process.remove(package)
            save_list_setting(pc_settings, pc_settings_filename(), 'in_process_packages', in_process)
