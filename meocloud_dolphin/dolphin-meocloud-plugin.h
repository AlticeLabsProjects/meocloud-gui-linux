#ifndef DolphinMEOCloudPlugin_H
#define DolphinMEOCloudPlugin_H

#include <kversioncontrolplugin.h>
#include <kabstractfileitemactionplugin.h>
#include <QDateTime>
#include <QHash>
#include <QVariantList>
#include <QFileInfo>
#include <QTimer>

class DolphinMEOCloudPlugin : public KVersionControlPlugin
{
    Q_OBJECT

public:
    DolphinMEOCloudPlugin(QObject* parent = 0, const QVariantList & args = QVariantList());
    virtual ~DolphinMEOCloudPlugin();
    virtual QString fileName() const;
    virtual bool beginRetrieval(const QString& directory);
    virtual void endRetrieval();
    virtual KVersionControlPlugin::VersionState versionState(const KFileItem& item);
    virtual QList<QAction*> contextMenuActions(const KFileItemList& items);
    virtual QList<QAction*> contextMenuActions(const QString& directory);

private slots:
    void shareFolderAction();
    void openInBrowserAction();
    void shareFileLinkAction();

private:
    QList<QAction*> getActions(QString url, bool is_dir);

    QAction* m_shareFolderAction;
    QAction* m_openInBrowserAction;
    QAction* m_shareFileLinkAction;

    void requestLink(QString path);
    void requestShare(QString path);
    void requestOpen(QString path);

    QString m_contextUrl;
    QHash<QString, KVersionControlPlugin::VersionState> m_versionInfoHash;
};
#endif // DolphinMEOCloudPlugin_H
