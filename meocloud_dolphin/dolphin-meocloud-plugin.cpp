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
#include <QSettings>
#include <KDE/KPluginFactory>
#include <KDE/KPluginLoader>
#include "dolphin-meocloud-plugin.h"

K_PLUGIN_FACTORY(DolphinMEOCloudPluginFactory, registerPlugin<DolphinMEOCloudPlugin>();)
K_EXPORT_PLUGIN(DolphinMEOCloudPluginFactory("dolphin-meocloud-plugin"))

DolphinMEOCloudPlugin::DolphinMEOCloudPlugin(QObject *parent, const QVariantList &args):
    KVersionControlPlugin(parent),
    m_versionInfoHash()
{
    Q_UNUSED(args);

    buffer = "";

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

    m_socket = new QLocalSocket(this);

    connect(m_socket, SIGNAL(connected()), this, SLOT(socket_connected()));
    connect(m_socket, SIGNAL(disconnected()), this, SLOT(socket_disconnected()));

    connect(m_socket, SIGNAL(readyRead()), this, SLOT(socket_readReady()));
    connect(m_socket, SIGNAL(error(QLocalSocket::LocalSocketError)),
            this, SLOT(socket_error(QLocalSocket::LocalSocketError)));

    reloadConfig();
}

DolphinMEOCloudPlugin::~DolphinMEOCloudPlugin()
{
    m_socket->abort();
    delete m_socket;
    m_socket = NULL;
}

/* SOCKETS */

void DolphinMEOCloudPlugin::subscribe() {
    m_socket->write("subscribe\t/\n");
    m_socket->flush();
}

void DolphinMEOCloudPlugin::requestStatus(QString path) {
	path = path.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n");
	m_socket->write(("status\t" + path.replace(m_cloudDir, "") + "\n").toStdString().c_str());
	m_socket->flush();
}

void DolphinMEOCloudPlugin::socket_connected() {
    subscribe();

    QTimer *timer = new QTimer(this);
	connect(timer, SIGNAL(timeout()), this, SLOT(reloadConfig()));
	timer->start(30000);
}

void DolphinMEOCloudPlugin::reloadConfig() {
    QFile checkConfig(QDir::homePath() + "/.meocloud/gui/prefs.ini");
	if(checkConfig.exists())
	{
		QSettings* settings = new QSettings(QDir::homePath() + "/.meocloud/gui/prefs.ini", QSettings::IniFormat);
		settings->beginGroup("Advanced");
		m_cloudDir = settings->value("Folder", QDir::homePath() + "/MEOCloud").toString();
		settings->endGroup();
	}
	else {
		m_cloudDir = QDir::homePath() + "/MEOCloud";
	}

    if (m_socket->state() == QLocalSocket::UnconnectedState) {
    	m_socket->connectToServer(QDir::homePath() + "/.meocloud/gui/meocloud_shell_proxy.socket");
    }
}

void DolphinMEOCloudPlugin::socket_disconnected() {
}

void DolphinMEOCloudPlugin::socket_readReady() {
    QDataStream in(m_socket);
    in.setVersion(QDataStream::Qt_4_0);

    if (m_socket->bytesAvailable() < (int)sizeof(quint64)) {
    		return;
    }

    if (in.atEnd())
        return;

    if (m_blockSize == 0) {
		if (m_socket->bytesAvailable() < (int)sizeof(quint64))
			return;
		in >> m_blockSize;
	}

    char* bufPtr = (char*)std::malloc(m_socket->bytesAvailable());
	int read = in.readRawData(bufPtr, m_socket->bytesAvailable());

	std::string stdString(bufPtr, read);
	QString data = QString::fromStdString(stdString);

	m_blockSize = 0;

    while (data.length() > 0) {
		int data_length = data.length();

		for (int i = 0; i < data.length(); i++) {
			if (data[i] == '\n') {
				processData(buffer + data.mid(0, i));
				buffer = "";
				data = data.mid(i+1, data.length() - (i+1));
				break;
			}
		}

		if (data_length == data.length()) {
			buffer += data;
			data = "";
			break;
		}
	}

	buffer += data;

	if (m_socket->bytesAvailable() >= (int)sizeof(quint64))
		socket_readReady();
}

void DolphinMEOCloudPlugin::processData(QString data) {
	QString command = data.split('\t')[0];
	QString path = data.split('\t')[1];
	QString state = data.split('\t')[2];

	path = path.replace("\\t", "\t").replace("\\n", "\n").replace("\\\\", "\\");

	if (path == "/")
		path = "";

	if (state == "1") {
		m_versionInfoHash.insert(m_cloudDir + path, KVersionControlPlugin::UpdateRequiredVersion);
	} else if (state == "2" || state == "3") {
		m_versionInfoHash.insert(m_cloudDir + path, KVersionControlPlugin::ConflictingVersion);
	} else if (state == "0") {
		m_versionInfoHash.insert(m_cloudDir + path, KVersionControlPlugin::NormalVersion);
	}

	setVersionState();
}

void DolphinMEOCloudPlugin::socket_error(QLocalSocket::LocalSocketError) {
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

		if (filename == m_cloudDir) {
			cloudIsHere = true;
			break;
		}
	}

    if (!directory.startsWith(m_cloudDir) && !cloudIsHere) {
        return true;
    }

    if (m_lastDir != dir.absolutePath()) {
    	m_lastDir = dir.absolutePath();
    	m_versionInfoHash.clear();
    }

    for(int i = 2; i < files.size(); ++i) {
        QString filename = dir.absolutePath() + QDir::separator() + files.at(i);
        KVersionControlPlugin::VersionState versionState;

        if (filename == m_cloudDir) {
        	if (!m_versionInfoHash.contains(filename)) {
				versionState = KVersionControlPlugin::UnversionedVersion;
				requestStatus(filename + "/");
			}
            return true;
        } else if (!cloudIsHere) {
        	if (!m_versionInfoHash.contains(filename)) {
        		versionState = KVersionControlPlugin::UnversionedVersion;
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

    if (!path.startsWith(m_cloudDir + "/"))
    	return actions;

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
	path = path.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n");
	m_socket->write(("link\t" + path.replace(m_cloudDir, "") + "\n").toStdString().c_str());
	m_socket->flush();
}

void DolphinMEOCloudPlugin::requestShare(QString path)
{
	path = path.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n");
	m_socket->write(("folder\t" + path.replace(m_cloudDir, "") + "\n").toStdString().c_str());
	m_socket->flush();
}

void DolphinMEOCloudPlugin::requestOpen(QString path)
{
	path = path.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n");
	m_socket->write(("browser\t" + path.replace(m_cloudDir, "") + "\n").toStdString().c_str());
	m_socket->flush();
}
