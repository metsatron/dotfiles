import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.FormLayout {
    property alias cfg_appName: appNameField.text
    property alias cfg_hideWhenMenuAvailable: hideCheck.checked
    property alias cfg_maxRecentItems: maxRecent.value

    QQC2.TextField {
        id: appNameField
        Kirigami.FormData.label: i18n("Menu title:")
    }

    QQC2.CheckBox {
        id: hideCheck
        Kirigami.FormData.label: i18n("Hide when a global menu is shown:")
    }

    QQC2.SpinBox {
        id: maxRecent
        from: 3
        to: 30
        Kirigami.FormData.label: i18n("Maximum recent items:")
    }
}
