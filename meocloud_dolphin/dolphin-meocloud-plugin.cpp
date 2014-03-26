#include <kaction.h>
#include <kactionmenu.h>
#include <kdemacros.h>
#include <kfileitem.h>
#include <klocalizedstring.h>
#include <kfileitemlistproperties.h>
#include <QDir>
#include <QFileInfo>
#include <QString>
#include <QStringList>
#include <QApplication>
#include <QClipboard>
#include <QtDBus>
#include <QtDebug>
#include <KDE/KPluginFactory>
#include <KDE/KPluginLoader>
#include "dolphin-meocloud-plugin.h"

K_PLUGIN_FACTORY(DolphinMEOCloudPluginFactory, registerPlugin<DolphinMEOCloudPlugin>();)
K_EXPORT_PLUGIN(DolphinMEOCloudPluginFactory("dolphin-meocloud-plugin"))

struct DolphinMEOCloudPlugin::Private
{
    QString contextFilePath;
};


DolphinMEOCloudPlugin::DolphinMEOCloudPlugin(QObject* parent, const QVariantList & args):
    KAbstractFileItemActionPlugin(parent)
{
    Q_UNUSED(args);
    p = new Private;

    // connect to core
    // p->core
}

DolphinMEOCloudPlugin::~DolphinMEOCloudPlugin()
{
    delete p;
}

QList<QAction*> DolphinMEOCloudPlugin::actions(const KFileItemListProperties & fileItemInfos, QWidget * parentWidget)
{
    Q_UNUSED(parentWidget);
    QList<QAction*> actions;

    if (fileItemInfos.items().count() != 1)
        return actions;

    KFileItem item = fileItemInfos.items().first();
    QString itemPath = item.localPath();
    QFileInfo itemFileInfo = QFileInfo(itemPath);

    QDBusMessage m = QDBusMessage::createMethodCall("pt.meocloud.dbus",
                                                    "/pt/meocloud/dbus",
                                                    "",
                                                    "FileInCloud");
    m << itemPath;
    QDBusMessage response = QDBusConnection::sessionBus().call(m);

    if (response.type() == QDBusMessage::ReplyMessage) {
        bool in_cloud = response.arguments().at(0).value<bool>();

        if (!in_cloud)
            return actions;
    } else {
        return actions;
    }

    KActionMenu * menuAction = new KActionMenu(this);
    menuAction->setText("MEO Cloud");
    actions << menuAction;

    p->contextFilePath = itemPath;

    QAction * openInBrowserAction = new KAction(this);
    openInBrowserAction->setIcon(KIcon("download-later"));
    openInBrowserAction->setText(i18nc("@item:inmenu", "Open in Browser"));
    menuAction->addAction(openInBrowserAction);
    connect(openInBrowserAction, SIGNAL(triggered()),
            this, SLOT(openInBrowserAction()));

    if (item.isDir()) {
        QAction * shareFolderAction = new KAction(this);
        shareFolderAction->setIcon(KIcon("download-later"));
        shareFolderAction->setText(i18nc("@item:inmenu", "Share Folder"));
        menuAction->addAction(shareFolderAction);
        connect(shareFolderAction, SIGNAL(triggered()),
                this, SLOT(shareFolderAction()));
    } else {
        QAction * shareLinkAction = new KAction(this);
        shareLinkAction->setIcon(KIcon("download-later"));
        shareLinkAction->setText(i18nc("@item:inmenu", "Copy Link"));
        menuAction->addAction(shareLinkAction);
        connect(shareLinkAction, SIGNAL(triggered()),
                this, SLOT(shareFileLinkAction()));
    }

    return actions;
}

void DolphinMEOCloudPlugin::shareFolderAction()
{
    this->requestShare(p->contextFilePath);
}

void DolphinMEOCloudPlugin::openInBrowserAction()
{
    this->requestOpen(p->contextFilePath);
}

void DolphinMEOCloudPlugin::shareFileLinkAction()
{
    this->requestLink(p->contextFilePath);
}

void DolphinMEOCloudPlugin::requestLink(QString path)
{
    QDBusMessage m = QDBusMessage::createMethodCall("pt.meocloud.dbus",
                                                    "/pt/meocloud/dbus",
                                                    "",
                                                    "ShareLink");
    m << path;
    QDBusMessage response = QDBusConnection::sessionBus().call(m);
}

void DolphinMEOCloudPlugin::requestShare(QString path)
{
    QDBusMessage m = QDBusMessage::createMethodCall("pt.meocloud.dbus",
                                                    "/pt/meocloud/dbus",
                                                    "",
                                                    "ShareFolder");
    m << path;
    QDBusMessage response = QDBusConnection::sessionBus().call(m);
}

void DolphinMEOCloudPlugin::requestOpen(QString path)
{
    QDBusMessage m = QDBusMessage::createMethodCall("pt.meocloud.dbus",
                                                    "/pt/meocloud/dbus",
                                                    "",
                                                    "OpenInBrowser");
    m << path;
    QDBusMessage response = QDBusConnection::sessionBus().call(m);
}
