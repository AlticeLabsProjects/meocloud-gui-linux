#ifndef SHELLBUS_H_1396017396
#define SHELLBUS_H_1396017396

#include <QtCore/QObject>
#include <QtDBus/QtDBus>
class QByteArray;
template<class T> class QList;
template<class Key, class Value> class QMap;
class QString;
class QStringList;
class QVariant;

/*
 * Adaptor class for interface pt.meocloud.shell
 */
class ShellAdaptor: public QDBusAbstractAdaptor
{
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface", "pt.meocloud.shell")
    Q_CLASSINFO("D-Bus Introspection", ""
"  <interface name=\"pt.meocloud.shell\">\n"
"    <method name=\"UpdateFile\">\n"
"      <arg direction=\"in\" type=\"s\" name=\"path\"/>\n"
"    </method>\n"
"  </interface>\n"
        "")
public:
    ShellAdaptor(QObject *parent);
    virtual ~ShellAdaptor();

public: // PROPERTIES
public Q_SLOTS: // METHODS
    void UpdateFile(const QString &path);
Q_SIGNALS: // SIGNALS
};

class ShellServer : public QObject
{
    Q_OBJECT
public:
    explicit ShellServer(QObject *parent = 0):
        QObject(parent)
    {
    }

public slots:
    void UpdateFile()
    {
        QMetaObject::invokeMethod(parent(), "setVersionState");
    }
signals:
    void responseFromServer(const QString &data);
};

#endif
