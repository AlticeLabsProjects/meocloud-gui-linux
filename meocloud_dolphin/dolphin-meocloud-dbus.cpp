#include "dolphin-meocloud-dbus.h"
#include <QtCore/QMetaObject>
#include <QtCore/QByteArray>
#include <QtCore/QList>
#include <QtCore/QMap>
#include <QtCore/QString>
#include <QtCore/QStringList>
#include <QtCore/QVariant>

/*
 * Implementation of adaptor class ShellAdaptor
 */

ShellAdaptor::ShellAdaptor(QObject *parent)
    : QDBusAbstractAdaptor(parent)
{
    // constructor
    setAutoRelaySignals(true);
}

ShellAdaptor::~ShellAdaptor()
{
    // destructor
}

void ShellAdaptor::UpdateFile(const QString &path)
{
    // do something with the path to get rid of the unused warning
    // even if it's just doing nothing
    (void)(path);

    // handle method call pt.meocloud.shell.UpdateFile
    QMetaObject::invokeMethod(parent(), "UpdateFile");
}
