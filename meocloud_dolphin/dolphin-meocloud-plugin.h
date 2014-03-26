#ifndef DolphinMEOCloudPlugin_H
#define DolphinMEOCloudPlugin_H

#include <kabstractfileitemactionplugin.h>
#include <QDateTime>
#include <QHash>
#include <QVariantList>
#include <QFileInfo>
#include <QTimer>

class DolphinMEOCloudPlugin : public KAbstractFileItemActionPlugin
{
    Q_OBJECT

public:
    DolphinMEOCloudPlugin(QObject* parent = 0, const QVariantList & args = QVariantList());
    virtual ~DolphinMEOCloudPlugin();
    virtual QList<QAction*> actions(const KFileItemListProperties & fileItemInfos, QWidget * parentWidget);

private slots:
    void shareFolderAction();
    void openInBrowserAction();
    void shareFileLinkAction();

private:
    struct Private;
    Private * p;
    void requestLink(QString path);
    void requestShare(QString path);
    void requestOpen(QString path);

};
#endif // DolphinMEOCloudPlugin_H
