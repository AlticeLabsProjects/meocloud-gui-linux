#include <kaction.h>
#include <kactionmenu.h>
#include <kdemacros.h>
#include <kfileitem.h>
#include <klocalizedstring.h>
#include <kfileitemlistproperties.h>
#include <QtCore/QDir>
#include <QtCore/QFileInfo>
#include <QtCore/QString>
#include <QtCore/QStringList>
#include <QtCore/QtDebug>
#include <QtGui/QApplication>
#include <QtGui/QClipboard>
#include <QLocalSocket>
#include <KDE/KPluginFactory>
#include <KDE/KPluginLoader>
#include "dolphin-meocloud-plugin.h"
#include "shell_types.h"

#include <protocol/TBinaryProtocol.h>
#include <protocol/TDenseProtocol.h>
#include <protocol/TJSONProtocol.h>
#include <transport/TTransportUtils.h>
#include <transport/TFDTransport.h>

K_PLUGIN_FACTORY(DolphinMEOCloudPluginFactory, registerPlugin<DolphinMEOCloudPlugin>();)
K_EXPORT_PLUGIN(DolphinMEOCloudPluginFactory("dolphin-meocloud-plugin"))

DolphinMEOCloudPlugin::DolphinMEOCloudPlugin(QObject *parent, const QVariantList &args):
    KVersionControlPlugin(parent),
    m_versionInfoHash()
{
    Q_UNUSED(args);

    QString lang = QLocale::system().uiLanguages().first().replace("-", "_");

    QString SHARE_STRING = "Share Folder";
    QString BROWSER_STRING = "Open in Browser";
    QString LINK_STRING = "Copy Link";

    if (lang == "pt" || lang == "pt_PT" || lang == "pt_BR") {
        SHARE_STRING = "Partilhar Pasta";
        BROWSER_STRING = "Abrir no browser";
        LINK_STRING = "Copiar link";
    }

    m_shareFolderAction = new KAction(this);
    m_shareFolderAction->setIcon(KIcon("internet-web-browser"));
    m_shareFolderAction->setText(SHARE_STRING);
    connect(m_shareFolderAction, SIGNAL(triggered()),
            this, SLOT(shareFolderAction()));

    m_openInBrowserAction = new KAction(this);
    m_openInBrowserAction->setIcon(KIcon("internet-web-browser"));
    m_openInBrowserAction->setText(BROWSER_STRING);
    connect(m_openInBrowserAction, SIGNAL(triggered()),
            this, SLOT(openInBrowserAction()));

    m_shareFileLinkAction = new KAction(this);
    m_shareFileLinkAction->setIcon(KIcon("internet-web-browser"));
    m_shareFileLinkAction->setText(LINK_STRING);
    connect(m_shareFileLinkAction, SIGNAL(triggered()),
            this, SLOT(shareFileLinkAction()));

    /*ShellServer *server = new ShellServer(this);
    new ShellAdaptor(server);

    QDBusConnection connection = QDBusConnection::sessionBus();
    connection.unregisterService("pt.meocloud.shell");
    bool registerSuccess = connection.registerService("pt.meocloud.shell");
    if (!registerSuccess) {
        qDebug() << "registerService failed :(";
    }

    connection.unregisterObject("/pt/meocloud/shell");
    registerSuccess = connection.registerObject("/pt/meocloud/shell", server);
    if (!registerSuccess) {
        qDebug() << "registerObject failed :(";
    }*/

    m_socket = new QLocalSocket(this);

    connect(m_socket, SIGNAL(connected()), this, SLOT(socket_connected()));
    connect(m_socket, SIGNAL(disconnected()), this, SLOT(socket_disconnected()));

    connect(m_socket, SIGNAL(readyRead()), this, SLOT(socket_readReady()));
    connect(m_socket, SIGNAL(error(QLocalSocket::LocalSocketError)),
            this, SLOT(socket_error(QLocalSocket::LocalSocketError)));

    m_socket->connectToServer("/home/ivo/.meocloud/gui/meocloud_shell_listener.socket");
}

DolphinMEOCloudPlugin::~DolphinMEOCloudPlugin()
{
    m_socket->abort();
    delete m_socket;
    m_socket = NULL;
}

/* SOCKETS */

void DolphinMEOCloudPlugin::subscribe() {
    Shell::SubscribeMessage msg;
    msg.type = Shell::SubscribeType::SUBSCRIBE;
    msg.path = "/";

    boost::shared_ptr<apache::thrift::transport::TMemoryBuffer> transportOut(new apache::thrift::transport::TMemoryBuffer());
    boost::shared_ptr<apache::thrift::protocol::TBinaryProtocol> protocolOut(new apache::thrift::protocol::TBinaryProtocol(transportOut));

    uint8_t* bufPtr;
    uint32_t sz;

    transportOut->resetBuffer();
    msg.write(protocolOut.get());
    transportOut->getBuffer(&bufPtr, &sz);
    transportOut->close();

    m_socket->write(QByteArray((const char*)bufPtr, sz));
    m_socket->flush();
}

void DolphinMEOCloudPlugin::requestStatus(QString path) {
    Shell::Message msg;
    msg.type = Shell::MessageType::FILE_STATUS;
    msg.fileStatus.type = Shell::FileStatusType::REQUEST;
    msg.fileStatus.status.path = path.replace("/home/ivo/MEOCloud", "").toStdString();
    msg.__isset.fileStatus = true;
    msg.fileStatus.__isset.status = true;

    qDebug() << "REQUESTING: " + QString::fromStdString(msg.fileStatus.status.path);

    boost::shared_ptr<apache::thrift::transport::TMemoryBuffer> transportOut(new apache::thrift::transport::TMemoryBuffer());
    boost::shared_ptr<apache::thrift::protocol::TBinaryProtocol> protocolOut(new apache::thrift::protocol::TBinaryProtocol(transportOut));

    uint8_t* bufPtr;
    uint32_t sz;

    transportOut->resetBuffer();
    msg.write(protocolOut.get());
    transportOut->getBuffer(&bufPtr, &sz);
    transportOut->close();

    m_socket->write(QByteArray((const char*)bufPtr, sz));
    m_socket->flush();
}

void DolphinMEOCloudPlugin::socket_connected(){
    qDebug() << "connected";
    subscribe();

    /*QTimer *timer = new QTimer(this);
	connect(timer, SIGNAL(timeout()), this, SLOT(socket_readReady()));
	timer->start(3000);*/
}

void DolphinMEOCloudPlugin::socket_disconnected() {
    qDebug() << "socket_disconnected";
}

void DolphinMEOCloudPlugin::socket_readReady() {
    qDebug() << "socket_readReady";

    QDataStream in(m_socket);
    in.setVersion(QDataStream::Qt_4_0);

    if (m_socket->bytesAvailable() < (int)sizeof(quint16)) {
    		qDebug() << "no data to be read";
    		return;
    }

    if (in.atEnd())
        return;

    char* bufPtr = (char*)std::malloc(m_socket->bytesAvailable());
	int read = in.readRawData(bufPtr, m_socket->bytesAvailable());

    Shell::Message msg;
    boost::shared_ptr<apache::thrift::transport::TMemoryBuffer> transportOut(new apache::thrift::transport::TMemoryBuffer((uint8_t*)bufPtr, read));
    boost::shared_ptr<apache::thrift::protocol::TBinaryProtocol> protocolOut(new apache::thrift::protocol::TBinaryProtocol(transportOut));
    msg.read(protocolOut.get());
    transportOut->close();

    qDebug() << "RECEIVED: " + QString::fromStdString(msg.fileStatus.status.path);

    if (msg.fileStatus.status.state == 1) {
		m_versionInfoHash.insert("/home/ivo/MEOCloud" + QString::fromUtf8(msg.fileStatus.status.path.c_str()), KVersionControlPlugin::UpdateRequiredVersion);
	} else if (msg.fileStatus.status.state == 2) {
		m_versionInfoHash.insert("/home/ivo/MEOCloud" + QString::fromUtf8(msg.fileStatus.status.path.c_str()), KVersionControlPlugin::ConflictingVersion);
	} else if (true) {
		m_versionInfoHash.insert("/home/ivo/MEOCloud" + QString::fromUtf8(msg.fileStatus.status.path.c_str()), KVersionControlPlugin::NormalVersion);
	}

    setVersionState();
}

void DolphinMEOCloudPlugin::socket_error(QLocalSocket::LocalSocketError) {
    qDebug() << "socket_error";
}

QString DolphinMEOCloudPlugin::fileName() const
{
    return QLatin1String(".meocloud");
}

bool DolphinMEOCloudPlugin::beginRetrieval(const QString &directory)
{
    Q_ASSERT(directory.endsWith(QLatin1Char('/')));

    bool cloudIsHere = false;
    QDir dir(directory);
    QStringList files = dir.entryList();

    for(int i = 2; i < files.size(); ++i) {
        QString filename = dir.absolutePath() + QDir::separator() + files.at(i);

        if(filename == "/home/ivo/MEOCloud") {
            cloudIsHere = true;
            break;
        }
    }

    if (!directory.startsWith("/home/ivo/MEOCloud") && !cloudIsHere) {
        return true;
    }

//m_versionInfoHash.clear();

    for(int i = 2; i < files.size(); ++i) {
        QString filename = dir.absolutePath() + QDir::separator() + files.at(i);
        KVersionControlPlugin::VersionState versionState;

        if (filename == "/home/ivo/MEOCloud") {
            return true;
        } else {
        	if (!m_versionInfoHash.contains(filename)) {
        		versionState = KVersionControlPlugin::UnversionedVersion;
        		m_versionInfoHash.insert(filename, versionState);
        		requestStatus(filename);
        	}
        }
    }

    return true;
}

void DolphinMEOCloudPlugin::endRetrieval()
{
}

KVersionControlPlugin::VersionState DolphinMEOCloudPlugin::versionState(const KFileItem &item)
{
    const QString itemUrl = item.localPath();

    if (m_versionInfoHash.contains(itemUrl)) {
        return m_versionInfoHash.value(itemUrl);
    }

    return KVersionControlPlugin::UnversionedVersion;
}

void DolphinMEOCloudPlugin::setVersionState()
{
    emit versionStatesChanged();
}

QList<QAction *>DolphinMEOCloudPlugin::contextMenuActions(const KFileItemList &items)
{
    Q_ASSERT(!items.isEmpty());

    if (items.size() > 1 || items.size() == 0) {
        QList<QAction *>emptyActions;
        m_contextUrl = QString();
        return emptyActions;
    }

    KFileItem item = items.at(0);
    return getActions(item.url().path(), item.isDir());
}

QList<QAction *>DolphinMEOCloudPlugin::contextMenuActions(const QString &directory)
{
    return getActions(directory, true);
}

QList<QAction *>DolphinMEOCloudPlugin::getActions(QString path, bool isDir)
{
    QList<QAction *>actions;

    /*QDBusMessage m = QDBusMessage::createMethodCall("pt.meocloud.dbus",
                                                    "/pt/meocloud/dbus",
                                                    "",
                                                    "FileInCloud");
    m << path;
    QDBusMessage response = QDBusConnection::sessionBus().call(m);

    if (response.type() == QDBusMessage::ReplyMessage) {
        bool inCloud = response.arguments().at(0).value<bool>();

        if (!inCloud) {
            return actions;
        }
    } else {
        return actions;
    }*/
    //return actions;

    m_contextUrl = path;

    KActionMenu *menuAction = new KActionMenu(this);
    menuAction->setText("MEO Cloud");

    menuAction->addAction(m_shareFileLinkAction);
    menuAction->addAction(m_openInBrowserAction);

    if (isDir) {
        menuAction->addAction(m_shareFolderAction);
    }

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
	path = path.replace("/home/ivo/MEOCloud", "");

	Shell::Message msg;
	msg.type = Shell::MessageType::SHARE;
	msg.share.path = path.toStdString();
	msg.share.type = Shell::ShareType::LINK;
	msg.__isset.share = true;

	boost::shared_ptr<apache::thrift::transport::TMemoryBuffer> transportOut(new apache::thrift::transport::TMemoryBuffer());
	boost::shared_ptr<apache::thrift::protocol::TBinaryProtocol> protocolOut(new apache::thrift::protocol::TBinaryProtocol(transportOut));

	uint8_t* bufPtr;
	uint32_t sz;

	transportOut->resetBuffer();
	msg.write(protocolOut.get());
	transportOut->getBuffer(&bufPtr, &sz);
	transportOut->close();

	m_socket->write(QByteArray((const char*)bufPtr, sz));
	m_socket->flush();
}

void DolphinMEOCloudPlugin::requestShare(QString path)
{
	path = path.replace("/home/ivo/MEOCloud", "");

	Shell::Message msg;
	msg.type = Shell::MessageType::SHARE;
	msg.share.path = path.toStdString();
	msg.share.type = Shell::ShareType::FOLDER;
	msg.__isset.share = true;

	boost::shared_ptr<apache::thrift::transport::TMemoryBuffer> transportOut(new apache::thrift::transport::TMemoryBuffer());
	boost::shared_ptr<apache::thrift::protocol::TBinaryProtocol> protocolOut(new apache::thrift::protocol::TBinaryProtocol(transportOut));

	uint8_t* bufPtr;
	uint32_t sz;

	transportOut->resetBuffer();
	msg.write(protocolOut.get());
	transportOut->getBuffer(&bufPtr, &sz);
	transportOut->close();

	m_socket->write(QByteArray((const char*)bufPtr, sz));
	m_socket->flush();
}

void DolphinMEOCloudPlugin::requestOpen(QString path)
{
	path = path.replace("/home/ivo/MEOCloud", "");

	Shell::Message msg;
	msg.type = Shell::MessageType::OPEN;
	msg.open.path = path.toStdString();
	msg.open.type = Shell::OpenType::BROWSER;
	msg.__isset.open = true;

	boost::shared_ptr<apache::thrift::transport::TMemoryBuffer> transportOut(new apache::thrift::transport::TMemoryBuffer());
	boost::shared_ptr<apache::thrift::protocol::TBinaryProtocol> protocolOut(new apache::thrift::protocol::TBinaryProtocol(transportOut));

	uint8_t* bufPtr;
	uint32_t sz;

	transportOut->resetBuffer();
	msg.write(protocolOut.get());
	transportOut->getBuffer(&bufPtr, &sz);
	transportOut->close();

	m_socket->write(QByteArray((const char*)bufPtr, sz));
	m_socket->flush();
}
