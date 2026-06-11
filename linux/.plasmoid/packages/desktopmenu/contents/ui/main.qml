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

        PC3.ToolButton {
            text: i18n("File")
            Layout.fillHeight: true
            onClicked: {
                fileMenu.visualParent = this;
                fileMenu.openRelative();
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
            onClicked: root.run("kdialog --title 'Desktop Menu' --msgbox " + root.quoteArg("DotCortex Desktop Menu 0.1.0 — macOS-style desktop menu bar for SonicDE/Plasma 6. Tangled from plasma.org."))
        }
    }
}
