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

DolphinMEOCloudPlugin::DolphinMEOCloudPlugin(QObject* parent, const QVariantList & args):
    KVersionControlPlugin(parent),
    m_versionInfoHash()
{
    Q_UNUSED(args);

    m_shareFolderAction = new KAction(this);
    m_shareFolderAction->setIcon(KIcon("internet-web-browser"));
    m_shareFolderAction->setText(i18nc("@item:inmenu", "Share Folder"));
    connect(m_shareFolderAction, SIGNAL(triggered()),
            this, SLOT(shareFolderAction()));

    m_openInBrowserAction = new KAction(this);
    m_openInBrowserAction->setIcon(KIcon("internet-web-browser"));
    m_openInBrowserAction->setText(i18nc("@item:inmenu", "Open in Browser"));
    connect(m_openInBrowserAction, SIGNAL(triggered()),
            this, SLOT(openInBrowserAction()));

    m_shareFileLinkAction = new KAction(this);
    m_shareFileLinkAction->setIcon(KIcon("internet-web-browser"));
    m_shareFileLinkAction->setText(i18nc("@item:inmenu", "Copy Link"));
    connect(m_shareFileLinkAction, SIGNAL(triggered()),
            this, SLOT(shareFileLinkAction()));
}

DolphinMEOCloudPlugin::~DolphinMEOCloudPlugin()
{
}

QString DolphinMEOCloudPlugin::fileName() const
{
    return QLatin1String(".meocloud");
}

bool DolphinMEOCloudPlugin::beginRetrieval(const QString& directory)
{
    Q_ASSERT(directory.endsWith(QLatin1Char('/')));

    QDBusMessage m = QDBusMessage::createMethodCall("pt.meocloud.dbus",
                                                    "/pt/meocloud/dbus",
                                                    "",
                                                    "GetCloudHome");
    QDBusMessage response = QDBusConnection::sessionBus().call(m);

    if (response.type() == QDBusMessage::ReplyMessage) {
        QString cloud_home = response.arguments().at(0).value<QString>();
        if (!directory.startsWith(cloud_home))
            return true;
    } else {
        return true;
    }

    m_versionInfoHash.clear();

    QDir dir(directory);
    QStringList files = dir.entryList();

    for(int i=2;i<files.size();++i)
    {
        QString filename = dir.absolutePath() + QDir::separator() + files.at(i);

        KVersionControlPlugin::VersionState versionstate = KVersionControlPlugin::UnversionedVersion;


        QDBusMessage m = QDBusMessage::createMethodCall("pt.meocloud.dbus",
                                                        "/pt/meocloud/dbus",
                                                        "",
                                                        "FileInCloud");
        m << filename;
        QDBusMessage response = QDBusConnection::sessionBus().call(m);

        if (response.type() == QDBusMessage::ReplyMessage) {
            bool in_cloud = response.arguments().at(0).value<bool>();
            bool is_syncing = response.arguments().at(1).value<bool>();

            if (in_cloud && is_syncing) {
                versionstate = KVersionControlPlugin::UpdateRequiredVersion;
                m_versionInfoHash.insert(filename, versionstate);
            } else if (in_cloud) {
                versionstate = KVersionControlPlugin::NormalVersion;
                m_versionInfoHash.insert(filename, versionstate);
            }
        }
    }

    return true;
}

void DolphinMEOCloudPlugin::endRetrieval()
{
}

KVersionControlPlugin::VersionState DolphinMEOCloudPlugin::versionState(const KFileItem& item)
{
    const QString itemUrl = item.localPath();

    if (m_versionInfoHash.contains(itemUrl))
    {
        return m_versionInfoHash.value(itemUrl);
    }

    return KVersionControlPlugin::UnversionedVersion;
}

QList<QAction*> DolphinMEOCloudPlugin::contextMenuActions(const KFileItemList& items)
{
    Q_ASSERT(!items.isEmpty());

    if(items.size() > 1 || items.size() == 0)
    {
        QList<QAction*> emptyactions;
        m_contextUrl = QString();
        return emptyactions;
    }

    KFileItem item = items.at(0);
    return getActions(item.url().path(), item.isDir());
}

QList<QAction*> DolphinMEOCloudPlugin::contextMenuActions(const QString& directory)
{
    return getActions(directory, true);
}

QList<QAction*> DolphinMEOCloudPlugin::getActions(QString path, bool is_dir)
{
    QList<QAction*> actions;

    QDBusMessage m = QDBusMessage::createMethodCall("pt.meocloud.dbus",
                                                    "/pt/meocloud/dbus",
                                                    "",
                                                    "FileInCloud");
    m << path;
    QDBusMessage response = QDBusConnection::sessionBus().call(m);

    if (response.type() == QDBusMessage::ReplyMessage) {
        bool in_cloud = response.arguments().at(0).value<bool>();

        if (!in_cloud)
            return actions;
    } else {
        return actions;
    }

    m_contextUrl = path;

    KActionMenu * menuAction = new KActionMenu(this);
    menuAction->setText("MEO Cloud");

    menuAction->addAction(m_openInBrowserAction);

    if (is_dir)
        menuAction->addAction(m_shareFolderAction);
    else
        menuAction->addAction(m_shareFileLinkAction);

    actions.append(menuAction);
    return actions;
}

void DolphinMEOCloudPlugin::shareFolderAction()
{
    this->requestShare(m_contextUrl);
}

void DolphinMEOCloudPlugin::openInBrowserAction()
{
    this->requestOpen(m_contextUrl);
}

void DolphinMEOCloudPlugin::shareFileLinkAction()
{
    this->requestLink(m_contextUrl);
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
