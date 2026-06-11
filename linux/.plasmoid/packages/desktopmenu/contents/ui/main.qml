import QtCore
import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.components as PC3
import org.kde.plasma.extras as PlasmaExtras
import org.kde.taskmanager as TaskManager
import org.kde.plasma.private.appmenu 1.0 as AppMenuPrivate
import org.kde.plasma.private.kicker as Kicker
import org.kde.plasma.plasma5support as P5Support

PlasmoidItem {
    id: root

    readonly property string appName: Plasmoid.configuration.appName
    readonly property int maxRecentItems: Plasmoid.configuration.maxRecentItems
    readonly property bool menuTakeover: appMenuModel.menuAvailable && Plasmoid.configuration.hideWhenMenuAvailable

    preferredRepresentation: fullRepresentation
    Plasmoid.constraintHints: Plasmoid.CanFillArea
    Plasmoid.status: menuTakeover ? PlasmaCore.Types.HiddenStatus : PlasmaCore.Types.ActiveStatus

    toolTipMainText: appName
    toolTipSubText: i18n("Desktop menu — shown when no application menu is active")

    function quoteArg(s) {
        return "'" + String(s).replace(/'/g, "'\\''") + "'";
    }

    function run(cmd) {
        executable.connectSource(cmd);
    }

    function openUrl(u) {
        run("xdg-open " + quoteArg(u));
    }

    P5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []
        onNewData: function (sourceName, data) {
            disconnectSource(sourceName);
        }
    }

    AppMenuPrivate.AppMenuModel {
        id: appMenuModel
        containmentStatus: Plasmoid.containment.status
        screenGeometry: root.screenGeometry
    }

    TaskManager.VirtualDesktopInfo {
        id: virtualDesktopInfo
    }

    TaskManager.ActivityInfo {
        id: activityInfo
    }

    TaskManager.TasksModel {
        id: tasksModel
        groupMode: TaskManager.TasksModel.GroupDisabled
        filterByVirtualDesktop: true
        filterByActivity: true
        virtualDesktop: virtualDesktopInfo.currentDesktop
        activity: activityInfo.currentActivity
    }

    Kicker.RecentUsageModel {
        id: recentModel
    }

    ListModel {
        id: placesModel
    }

    ListModel {
        id: templatesModel
    }

    // QML XHR cannot read local files (Qt 6 default); fetch via `cat` instead.
    P5Support.DataSource {
        id: placesReader
        engine: "executable"
        connectedSources: []
        onNewData: function (sourceName, data) {
            disconnectSource(sourceName);
            root.parsePlaces(data.stdout || "");
        }
    }

    P5Support.DataSource {
        id: templatesReader
        engine: "executable"
        connectedSources: []
        onNewData: function (sourceName, data) {
            disconnectSource(sourceName);
            root.parseTemplates(data.stdout || "");
        }
    }

    P5Support.DataSource {
        id: desktopStateReader
        engine: "executable"
        connectedSources: []
        onNewData: function (sourceName, data) {
            disconnectSource(sourceName);
            root.parseDesktopState(data.stdout || "");
        }
    }

    function decodeEntities(s) {
        return s.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, "\"").replace(/&apos;/g, "'").replace(/&amp;/g, "&");
    }

    function parsePlaces(xml) {
        placesModel.clear();
        const re = /<bookmark href="([^"]*)">([\s\S]*?)<\/bookmark>/g;
        let m;
        while ((m = re.exec(xml)) !== null) {
            const href = decodeEntities(m[1]);
            const body = m[2];
            if (/<isHidden>true<\/isHidden>/.test(body))
                continue;
            if (/<OnlyInApp>[^<]+<\/OnlyInApp>/.test(body))
                continue;
            const tm = body.match(/<title>([^<]*)<\/title>/);
            if (!tm)
                continue;
            const im = body.match(/<bookmark:icon name="([^"]*)"/);
            placesModel.append({
                title: decodeEntities(tm[1]),
                href: href,
                iconName: im ? im[1] : "folder"
            });
        }
    }

    function reloadPlaces() {
        const path = String(StandardPaths.writableLocation(StandardPaths.GenericDataLocation)).replace(/^file:\/\//, "") + "/user-places.xbel";
        placesReader.connectSource("cat " + quoteArg(path));
    }

    function templateIcon(name) {
        const lower = String(name).toLowerCase();
        if (lower.endsWith(".desktop"))
            return "application-x-desktop";
        if (lower.endsWith(".txt") || lower.endsWith(".md") || lower.endsWith(".org"))
            return "text-x-generic";
        if (lower.endsWith(".odt") || lower.endsWith(".doc") || lower.endsWith(".docx"))
            return "x-office-document";
        if (lower.endsWith(".ods") || lower.endsWith(".xls") || lower.endsWith(".xlsx"))
            return "x-office-spreadsheet";
        if (lower.endsWith(".odp") || lower.endsWith(".ppt") || lower.endsWith(".pptx"))
            return "x-office-presentation";
        return "document-new";
    }

    function parseTemplates(output) {
        templatesModel.clear();
        const lines = String(output).split("\n");
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (!line)
                continue;
            const tab = line.indexOf("\t");
            if (tab < 0)
                continue;
            const path = line.slice(0, tab);
            const name = line.slice(tab + 1);
            templatesModel.append({
                path: path,
                name: name,
                iconName: templateIcon(name)
            });
        }
    }

    function reloadTemplates() {
        const dir = String(StandardPaths.writableLocation(StandardPaths.HomeLocation)).replace(/^file:\/\//, "") + "/Templates";
        templatesReader.connectSource("bash -c " + quoteArg("mkdir -p \"$1\" && find \"$1\" -maxdepth 1 -mindepth 1 \\( -type f -o -type l \\) -printf '%p\\t%f\\n' | sort") + " _ " + quoteArg(dir));
    }

    function createFromTemplate(path, name) {
        root.run("bash -c " + root.quoteArg("name=$(kdialog --title 'Create From Template' --inputbox 'File name:' \"$2\") && [ -n \"$name\" ] && cp -R -- \"$1\" \"$HOME/Desktop/$name\"") + " _ " + root.quoteArg(path) + " " + root.quoteArg(name));
    }

    function homeBin(name) {
        return String(StandardPaths.writableLocation(StandardPaths.HomeLocation)).replace(/^file:\/\//, "") + "/.local/bin/" + name;
    }

    function effectiveInt(value, fallback) {
        if (value === undefined || value === null || value === "")
            return fallback;
        const parsed = parseInt(value);
        return isNaN(parsed) ? fallback : parsed;
    }

    function effectiveBool(value, fallback) {
        if (value === undefined || value === null || value === "")
            return fallback;
        if (value === true || value === "true" || value === "1")
            return true;
        if (value === false || value === "false" || value === "0")
            return false;
        return fallback;
    }

    function reloadDesktopState() {
        desktopStateReader.connectSource(homeBin("plasma-desktop-containment-report"));
    }

    function writeDesktopKey(key, value) {
        root.run("bash -lc " + root.quoteArg(homeBin("plasma-desktop-containment-set") + " " + root.quoteArg(key) + " " + root.quoteArg(value) + " >>/tmp/dotcortex-desktopmenu-actions.log 2>&1"));
        Qt.callLater(root.reloadDesktopState);
    }

    function parseDesktopState(output) {
        let report;
        try {
            report = JSON.parse(output);
        } catch (e) {
            return;
        }
        if (!report || report.length < 1 || !report[0].keys)
            return;

        const keys = report[0].keys;
        const sortMode = effectiveInt(keys.sortMode, 0);
        const iconSize = effectiveInt(keys.iconSize, 3);
        const arrangement = effectiveInt(keys.arrangement, 0);
        const alignment = effectiveInt(keys.alignment, 0);

        sortUnsortedItem.checked = sortMode === -1;
        sortNameItem.checked = sortMode === 0;
        sortSizeItem.checked = sortMode === 1;
        sortTypeItem.checked = sortMode === 6;
        sortDateItem.checked = sortMode === 2;
        sortDescendingItem.checked = effectiveBool(keys.sortDesc, false);
        sortFoldersFirstItem.checked = effectiveBool(keys.sortDirsFirst, true);

        iconTinyItem.checked = iconSize === 0;
        iconVerySmallItem.checked = iconSize === 1;
        iconSmallItem.checked = iconSize === 2;
        iconSmallMediumItem.checked = iconSize === 3;
        iconMediumItem.checked = iconSize === 4;
        iconLargeItem.checked = iconSize === 5;
        iconHugeItem.checked = iconSize === 6;

        arrangeLeftToRightItem.checked = arrangement === 0;
        arrangeTopToBottomItem.checked = arrangement === 1;
        alignLeftItem.checked = alignment === 0;
        alignRightItem.checked = alignment === 1;
        previewsItem.checked = effectiveBool(keys.previews, true);
        lockedItem.checked = effectiveBool(keys.locked, false);
    }

    function setDesktopSortMode(mode) {
        sortUnsortedItem.checked = mode === -1;
        sortNameItem.checked = mode === 0;
        sortSizeItem.checked = mode === 1;
        sortTypeItem.checked = mode === 6;
        sortDateItem.checked = mode === 2;
        writeDesktopKey("sortMode", mode);
    }

    function setDesktopIconSize(size) {
        iconTinyItem.checked = size === 0;
        iconVerySmallItem.checked = size === 1;
        iconSmallItem.checked = size === 2;
        iconSmallMediumItem.checked = size === 3;
        iconMediumItem.checked = size === 4;
        iconLargeItem.checked = size === 5;
        iconHugeItem.checked = size === 6;
        writeDesktopKey("iconSize", size);
    }

    function setDesktopArrangement(value) {
        arrangeLeftToRightItem.checked = value === 0;
        arrangeTopToBottomItem.checked = value === 1;
        writeDesktopKey("arrangement", value);
    }

    function setDesktopAlignment(value) {
        alignLeftItem.checked = value === 0;
        alignRightItem.checked = value === 1;
        writeDesktopKey("alignment", value);
    }

    Component.onCompleted: reloadPlaces()

    fullRepresentation: RowLayout {
        id: bar

        spacing: 0
        Layout.minimumWidth: implicitWidth
        Layout.minimumHeight: implicitHeight

        PC3.ToolButton {
            text: root.appName
            font.bold: true
            Layout.fillHeight: true
            onClicked: {
                appMenu.visualParent = this;
                appMenu.openRelative();
            }
        }

        Item {
            Layout.preferredWidth: 20
            Layout.fillHeight: true
        }

        PC3.ToolButton {
            text: i18n("File")
            Layout.fillHeight: true
            onClicked: {
                fileMenu.visualParent = this;
                fileMenu.openRelative();
            }
        }

        PC3.ToolButton {
            text: i18n("Edit")
            Layout.fillHeight: true
            onClicked: {
                editMenu.visualParent = this;
                editMenu.openRelative();
                Qt.callLater(function () {
                    root.reloadTemplates();
                    root.reloadDesktopState();
                });
            }
        }

        PC3.ToolButton {
            text: i18n("Go")
            Layout.fillHeight: true
            onClicked: {
                root.reloadPlaces();
                goMenu.visualParent = this;
                goMenu.openRelative();
            }
        }

        PC3.ToolButton {
            text: i18n("Recent")
            Layout.fillHeight: true
            onClicked: {
                recentMenu.visualParent = this;
                recentMenu.openRelative();
            }
        }

        PC3.ToolButton {
            text: i18n("Windows")
            Layout.fillHeight: true
            onClicked: {
                windowsMenu.visualParent = this;
                windowsMenu.openRelative();
            }
        }

        PC3.ToolButton {
            text: i18n("Help")
            Layout.fillHeight: true
            onClicked: {
                helpMenu.visualParent = this;
                helpMenu.openRelative();
            }
        }

        Item {
            Layout.preferredWidth: 0
            Layout.preferredHeight: 0
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }

    PlasmaExtras.Menu {
        id: appMenu

        placement: PlasmaExtras.Menu.BottomPosedLeftAlignedPopup

        PlasmaExtras.MenuItem {
            text: i18n("About This Computer")
            icon: "computer"
            onClicked: root.run("bash -c " + root.quoteArg(". /etc/os-release && kdialog --title 'About This Computer' --msgbox \"$PRETTY_NAME\nKernel: $(uname -r)\nHost: $(hostname)\nMemory: $(free -h | awk '/^Mem:/{print $2}')\""))
        }

        PlasmaExtras.MenuItem {
            text: i18n("System Settings…")
            icon: "configure"
            onClicked: root.run("systemsettings")
        }

        PlasmaExtras.MenuItem {
            separator: true
        }

        PlasmaExtras.MenuItem {
            text: i18n("Lock Screen")
            icon: "system-lock-screen"
            onClicked: root.run("qdbus6 org.freedesktop.ScreenSaver /ScreenSaver Lock")
        }

        PlasmaExtras.MenuItem {
            text: i18n("Leave…")
            icon: "system-log-out"
            onClicked: root.run("qdbus6 org.kde.LogoutPrompt /LogoutPrompt promptAll")
        }
    }

    PlasmaExtras.Menu {
        id: fileMenu

        placement: PlasmaExtras.Menu.BottomPosedLeftAlignedPopup

        PlasmaExtras.MenuItem {
            text: i18n("New Folder on Desktop…")
            icon: "folder-new"
            onClicked: root.run("bash -c " + root.quoteArg("name=$(kdialog --title 'New Folder' --inputbox 'Folder name:' 'New Folder') && mkdir -p \"$HOME/Desktop/$name\""))
        }

        PlasmaExtras.MenuItem {
            text: i18n("Open Desktop Folder")
            icon: "user-desktop"
            onClicked: root.openUrl(StandardPaths.writableLocation(StandardPaths.DesktopLocation))
        }

        PlasmaExtras.MenuItem {
            separator: true
        }

        PlasmaExtras.MenuItem {
            text: i18n("New File Manager Window")
            icon: "system-file-manager"
            onClicked: root.run("dolphin")
        }

        PlasmaExtras.MenuItem {
            text: i18n("New Terminal")
            icon: "utilities-terminal"
            onClicked: root.run("konsole")
        }

        PlasmaExtras.MenuItem {
            separator: true
        }

        PlasmaExtras.MenuItem {
            text: i18n("Open Trash")
            icon: "user-trash"
            onClicked: root.openUrl("trash:/")
        }
    }

    PlasmaExtras.Menu {
        id: editMenu

        placement: PlasmaExtras.Menu.BottomPosedLeftAlignedPopup

        PlasmaExtras.MenuItem {
            text: i18n("Desktop and Wallpaper\tAlt+D, Alt+S")
            icon: "preferences-desktop-wallpaper"
            onClicked: root.run("kcmshell6 kcm_wallpaper")
        }

        PlasmaExtras.MenuItem {
            text: i18n("Display Configuration")
            icon: "preferences-desktop-display"
            onClicked: root.run("kcmshell6 kcm_kscreen")
        }

        PlasmaExtras.MenuItem {
            separator: true
        }

        PlasmaExtras.MenuItem {
            id: createNewMenuItem

            text: i18n("Create New")
            icon: "document-new"
            readonly property PlasmaExtras.Menu submenu: PlasmaExtras.Menu {
                visualParent: createNewMenuItem.action

                PlasmaExtras.MenuItem {
                    text: i18n("Folder…")
                    icon: "folder-new"
                    onClicked: root.run("bash -c " + root.quoteArg("name=$(kdialog --title 'New Folder' --inputbox 'Folder name:' 'New Folder') && mkdir -p \"$HOME/Desktop/$name\""))
                }

                PlasmaExtras.MenuItem {
                    text: i18n("Text File…")
                    icon: "text-x-generic"
                    onClicked: root.run("bash -c " + root.quoteArg("name=$(kdialog --title 'New Text File' --inputbox 'File name:' 'New Text File.txt') && : > \"$HOME/Desktop/$name\""))
                }

                PlasmaExtras.MenuItem {
                    text: i18n("Empty File…")
                    icon: "document-new"
                    onClicked: root.run("bash -c " + root.quoteArg("name=$(kdialog --title 'New Empty File' --inputbox 'File name:' 'New File') && : > \"$HOME/Desktop/$name\""))
                }

                PlasmaExtras.MenuItem {
                    text: i18n("Link to Location (URL)…")
                    icon: "insert-link"
                    onClicked: root.run("bash -c " + root.quoteArg("url=$(kdialog --title 'Link to Location' --inputbox 'URL:' 'https://') && name=$(kdialog --title 'Link Name' --inputbox 'Name:' 'New Link.desktop') && printf '[Desktop Entry]\\nType=Link\\nURL=%s\\nName=%s\\nIcon=internet-web-browser\\n' \"$url\" \"${name%.desktop}\" > \"$HOME/Desktop/${name%.desktop}.desktop\" && chmod +x \"$HOME/Desktop/${name%.desktop}.desktop\""))
                }

                PlasmaExtras.MenuItem {
                    separator: true
                }

                PlasmaExtras.MenuItem {
                    id: templateSeparator

                    separator: true
                    visible: templatesModel.count > 0
                }

                PlasmaExtras.MenuItem {
                    text: i18n("Open Templates Folder")
                    icon: "folder-templates"
                    onClicked: root.openUrl(StandardPaths.writableLocation(StandardPaths.HomeLocation) + "/Templates")
                }
            }
        }

        PlasmaExtras.MenuItem {
            id: iconsMenuItem

            text: i18n("Icons")
            icon: "preferences-desktop-icons"
            readonly property PlasmaExtras.Menu submenu: PlasmaExtras.Menu {
                visualParent: iconsMenuItem.action

                PlasmaExtras.MenuItem {
                    id: sortByMenuItem

                    text: i18n("Sort By")
                    icon: "view-sort-ascending"
                    readonly property PlasmaExtras.Menu submenu: PlasmaExtras.Menu {
                        visualParent: sortByMenuItem.action

                        PlasmaExtras.MenuItem { id: sortUnsortedItem; text: i18n("Unsorted"); checkable: true; onClicked: root.setDesktopSortMode(-1) }
                        PlasmaExtras.MenuItem { id: sortNameItem; text: i18n("Name"); checkable: true; checked: true; onClicked: root.setDesktopSortMode(0) }
                        PlasmaExtras.MenuItem { id: sortSizeItem; text: i18n("Size"); checkable: true; onClicked: root.setDesktopSortMode(1) }
                        PlasmaExtras.MenuItem { id: sortTypeItem; text: i18n("Type"); checkable: true; onClicked: root.setDesktopSortMode(6) }
                        PlasmaExtras.MenuItem { id: sortDateItem; text: i18n("Date"); checkable: true; onClicked: root.setDesktopSortMode(2) }

                        PlasmaExtras.MenuItem {
                            separator: true
                        }

                        PlasmaExtras.MenuItem { id: sortDescendingItem; text: i18n("Descending"); checkable: true; onClicked: root.writeDesktopKey("sortDesc", sortDescendingItem.checked ? "true" : "false") }
                        PlasmaExtras.MenuItem { id: sortFoldersFirstItem; text: i18n("Folders First"); checkable: true; checked: true; onClicked: root.writeDesktopKey("sortDirsFirst", sortFoldersFirstItem.checked ? "true" : "false") }
                    }
                }

                PlasmaExtras.MenuItem {
                    id: iconSizeMenuItem

                    text: i18n("Icon Size")
                    icon: "zoom-fit-best"
                    readonly property PlasmaExtras.Menu submenu: PlasmaExtras.Menu {
                        visualParent: iconSizeMenuItem.action

                        PlasmaExtras.MenuItem { id: iconTinyItem; text: i18n("Tiny"); checkable: true; onClicked: root.setDesktopIconSize(0) }
                        PlasmaExtras.MenuItem { id: iconVerySmallItem; text: i18n("Very Small"); checkable: true; onClicked: root.setDesktopIconSize(1) }
                        PlasmaExtras.MenuItem { id: iconSmallItem; text: i18n("Small"); checkable: true; onClicked: root.setDesktopIconSize(2) }
                        PlasmaExtras.MenuItem { id: iconSmallMediumItem; text: i18n("Small-Medium"); checkable: true; checked: true; onClicked: root.setDesktopIconSize(3) }
                        PlasmaExtras.MenuItem { id: iconMediumItem; text: i18n("Medium"); checkable: true; onClicked: root.setDesktopIconSize(4) }
                        PlasmaExtras.MenuItem { id: iconLargeItem; text: i18n("Large"); checkable: true; onClicked: root.setDesktopIconSize(5) }
                        PlasmaExtras.MenuItem { id: iconHugeItem; text: i18n("Huge"); checkable: true; onClicked: root.setDesktopIconSize(6) }
                    }
                }

                PlasmaExtras.MenuItem {
                    id: arrangeMenuItem

                    text: i18n("Arrange")
                    icon: "view-list-icons"
                    readonly property PlasmaExtras.Menu submenu: PlasmaExtras.Menu {
                        visualParent: arrangeMenuItem.action

                        PlasmaExtras.MenuItem { id: arrangeLeftToRightItem; text: i18n("Left to Right"); checkable: true; checked: true; onClicked: root.setDesktopArrangement(0) }
                        PlasmaExtras.MenuItem { id: arrangeTopToBottomItem; text: i18n("Top to Bottom"); checkable: true; onClicked: root.setDesktopArrangement(1) }
                    }
                }

                PlasmaExtras.MenuItem {
                    id: alignMenuItem

                    text: i18n("Align")
                    icon: "align-horizontal-left"
                    readonly property PlasmaExtras.Menu submenu: PlasmaExtras.Menu {
                        visualParent: alignMenuItem.action

                        PlasmaExtras.MenuItem { id: alignLeftItem; text: i18n("Left"); checkable: true; checked: true; onClicked: root.setDesktopAlignment(0) }
                        PlasmaExtras.MenuItem { id: alignRightItem; text: i18n("Right"); checkable: true; onClicked: root.setDesktopAlignment(1) }
                    }
                }

                PlasmaExtras.MenuItem {
                    separator: true
                }

                PlasmaExtras.MenuItem {
                    id: previewsItem

                    text: i18n("Show Previews")
                    icon: "view-preview"
                    checkable: true
                    checked: true
                    onClicked: root.writeDesktopKey("previews", previewsItem.checked ? "true" : "false")
                }

                PlasmaExtras.MenuItem {
                    id: lockedItem

                    text: i18n("Locked")
                    icon: "object-locked"
                    checkable: true
                    checked: false
                    onClicked: root.writeDesktopKey("locked", lockedItem.checked ? "true" : "false")
                }
            }
        }

        PlasmaExtras.MenuItem {
            text: i18n("Paste Clipboard Contents\tCtrl+V")
            icon: "edit-paste"
            onClicked: root.run("xdotool key ctrl+v")
        }

        PlasmaExtras.MenuItem {
            text: i18n("Undo\tCtrl+Z")
            icon: "edit-undo"
            onClicked: root.run("xdotool key ctrl+z")
        }

        PlasmaExtras.MenuItem {
            separator: true
        }

        PlasmaExtras.MenuItem {
            text: i18n("Enter Edit Mode")
            icon: "document-edit"
            onClicked: Plasmoid.containment.corona.editMode = true
        }
    }

    Instantiator {
        model: templatesModel
        delegate: PlasmaExtras.MenuItem {
            text: model.name
            icon: model.iconName
            onClicked: root.createFromTemplate(model.path, model.name)
        }
        onObjectAdded: (index, object) => createNewMenuItem.submenu.addMenuItem(object, templateSeparator)
        onObjectRemoved: (index, object) => createNewMenuItem.submenu.removeMenuItem(object)
    }

    PlasmaExtras.Menu {
        id: goMenu

        placement: PlasmaExtras.Menu.BottomPosedLeftAlignedPopup

        PlasmaExtras.MenuItem {
            id: goSeparator
            separator: true
        }

        PlasmaExtras.MenuItem {
            text: i18n("Go to Folder…")
            icon: "folder-open"
            onClicked: root.run("bash -c " + root.quoteArg("d=$(kdialog --title 'Go to Folder' --getexistingdirectory \"$HOME\") && xdg-open \"$d\""))
        }
    }

    Instantiator {
        model: placesModel
        delegate: PlasmaExtras.MenuItem {
            text: model.title
            icon: model.iconName
            onClicked: root.openUrl(model.href)
        }
        onObjectAdded: (index, object) => goMenu.addMenuItem(object, goSeparator)
        onObjectRemoved: (index, object) => goMenu.removeMenuItem(object)
    }

    PlasmaExtras.Menu {
        id: recentMenu

        placement: PlasmaExtras.Menu.BottomPosedLeftAlignedPopup
    }

    Instantiator {
        model: recentModel
        delegate: PlasmaExtras.MenuItem {
            visible: index < root.maxRecentItems
            text: model.display || ""
            icon: model.decoration
            onClicked: recentModel.trigger(index, "", null)
        }
        onObjectAdded: (index, object) => recentMenu.addMenuItem(object)
        onObjectRemoved: (index, object) => recentMenu.removeMenuItem(object)
    }

    PlasmaExtras.Menu {
        id: windowsMenu

        placement: PlasmaExtras.Menu.BottomPosedLeftAlignedPopup
    }

    Instantiator {
        model: tasksModel
        delegate: PlasmaExtras.MenuItem {
            text: model.display || ""
            icon: model.decoration
            checkable: true
            checked: model.IsActive === true
            onClicked: tasksModel.requestActivate(tasksModel.makeModelIndex(index))
        }
        onObjectAdded: (index, object) => windowsMenu.addMenuItem(object)
        onObjectRemoved: (index, object) => windowsMenu.removeMenuItem(object)
    }

    PlasmaExtras.Menu {
        id: helpMenu

        placement: PlasmaExtras.Menu.BottomPosedLeftAlignedPopup

        PlasmaExtras.MenuItem {
            text: i18n("About This System")
            icon: "help-about"
            onClicked: root.run("bash -c " + root.quoteArg(". /etc/os-release && kdialog --title 'About This System' --msgbox \"$PRETTY_NAME\n$HOME_URL\""))
        }

        PlasmaExtras.MenuItem {
            text: i18n("About Desktop Menu")
            icon: "user-desktop"
            onClicked: root.run("kdialog --title 'Desktop Menu' --msgbox " + root.quoteArg("DotCortex Desktop Menu 0.1.5 — macOS-style desktop menu bar for SonicDE/Plasma 6. Tangled from plasma.org."))
        }
    }
}
