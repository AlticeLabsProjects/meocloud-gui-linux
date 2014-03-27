#include <unistd.h>
#include <gio/gio.h>
#include <dbus/dbus.h>
#include <dbus/dbus-glib.h>

#include "cloud-provider.h"

static void cloud_provider_menu_provider_init(ThunarxMenuProviderIface * iface);
static void cloud_provider_finalize(GObject * object);
static GList * cloud_provider_get_file_actions(
    ThunarxMenuProvider * menu_provider, GtkWidget * window, GList * files);

struct _CloudProviderClass
{
    GObjectClass __parent__;
};

struct _CloudProvider
{
    GObject __parent__;
};

THUNARX_DEFINE_TYPE_WITH_CODE (CloudProvider,
    cloud_provider,
    G_TYPE_OBJECT,
    THUNARX_IMPLEMENT_INTERFACE (THUNARX_TYPE_MENU_PROVIDER,
        cloud_provider_menu_provider_init));

static void cloud_provider_class_init(CloudProviderClass * klass)
{
    GObjectClass * gobject_class;

    gobject_class = G_OBJECT_CLASS(klass);
    gobject_class->finalize = cloud_provider_finalize;
}

static void cloud_provider_menu_provider_init(ThunarxMenuProviderIface * iface)
{
    iface->get_file_actions = cloud_provider_get_file_actions;
}

static void cloud_provider_init(CloudProvider * cloud_provider)
{

}

static void cloud_provider_finalize(GObject * object)
{
    CloudProvider * cloud_provider = CLOUD_PROVIDER(object);

    (*G_OBJECT_CLASS(cloud_provider_parent_class)->finalize)(object);
}

static void cloud_callback(GtkAction * action, gpointer data)
{
    GList * actioninfo = (GList*)data;
    gchar * verb = NULL;

    if(actioninfo == NULL)
        return;

    verb = actioninfo->data;
    actioninfo = actioninfo->next;
}

static void cloud_closure_destroy_notify(gpointer data, GClosure * closure)
{
    GList * actioninfo = (GList*)data;
    GList * lp;

    for(lp = actioninfo; lp != NULL; lp = lp->next)
    {
        g_free(lp->data);
    }

    g_list_free(actioninfo);
}

static void cloud_copy_link(GtkAction *action,
                            GtkWidget *window)
{
    GList *files;
    GFile *file;
    gchar *path;

    files = g_object_get_qdata (G_OBJECT (action), "meocloud-selected-files");
    if (G_UNLIKELY (files == NULL))
        return;

    file = thunarx_file_info_get_location(files->data);
	path = g_file_get_path(file);

    DBusGConnection *connection;
    GError *error;
    DBusGProxy *proxy;

    error = NULL;
    connection = dbus_g_bus_get (DBUS_BUS_SESSION,
                                 &error);
    if (connection == NULL)
    {
        g_error_free (error);
        return NULL;
    }

    proxy = dbus_g_proxy_new_for_name (connection,
                                       "pt.meocloud.dbus",
                                       "/pt/meocloud/dbus",
                                       "pt.meocloud.dbus");

    error = NULL;
    if (!dbus_g_proxy_call (proxy, "ShareLink", &error, G_TYPE_STRING,
                            path, G_TYPE_INVALID, G_TYPE_INVALID))
    {
        g_error_free (error);
        return NULL;
    }

    g_object_unref (proxy);
}

static void cloud_share_folder(GtkAction *action,
                               GtkWidget *window)
{
    GList *files;
    GFile *file;
    gchar *path;

    files = g_object_get_qdata (G_OBJECT (action), "meocloud-selected-files");
    if (G_UNLIKELY (files == NULL))
        return;

    file = thunarx_file_info_get_location(files->data);
	path = g_file_get_path(file);

    DBusGConnection *connection;
    GError *error;
    DBusGProxy *proxy;

    error = NULL;
    connection = dbus_g_bus_get (DBUS_BUS_SESSION,
                                 &error);
    if (connection == NULL)
    {
        g_error_free (error);
        return NULL;
    }

    proxy = dbus_g_proxy_new_for_name (connection,
                                       "pt.meocloud.dbus",
                                       "/pt/meocloud/dbus",
                                       "pt.meocloud.dbus");

    error = NULL;
    if (!dbus_g_proxy_call (proxy, "ShareFolder", &error, G_TYPE_STRING,
                            path, G_TYPE_INVALID, G_TYPE_INVALID))
    {
        g_error_free (error);
        return NULL;
    }

    g_object_unref (proxy);
}

static void cloud_open_in_browser(GtkAction *action,
                                  GtkWidget *window)
{
    GList *files;
    GFile *file;
    gchar *path;

    files = g_object_get_qdata (G_OBJECT (action), "meocloud-selected-files");
    if (G_UNLIKELY (files == NULL))
        return;

    file = thunarx_file_info_get_location(files->data);
	path = g_file_get_path(file);

    DBusGConnection *connection;
    GError *error;
    DBusGProxy *proxy;

    error = NULL;
    connection = dbus_g_bus_get (DBUS_BUS_SESSION,
                                 &error);
    if (connection == NULL)
    {
        g_error_free (error);
        return NULL;
    }

    proxy = dbus_g_proxy_new_for_name (connection,
                                       "pt.meocloud.dbus",
                                       "/pt/meocloud/dbus",
                                       "pt.meocloud.dbus");

    error = NULL;
    if (!dbus_g_proxy_call (proxy, "OpenInBrowser", &error, G_TYPE_STRING,
                            path, G_TYPE_INVALID, G_TYPE_INVALID))
    {
        g_error_free (error);
        return NULL;
    }

    g_object_unref (proxy);
}

static GList * cloud_provider_get_file_actions(
    ThunarxMenuProvider * menu_provider,
    GtkWidget * window,
    GList * files)
{
    GFile * file;
    GList * actions = NULL;
    GtkAction *action;
    GClosure *closure;
    CloudProvider *cloud_provider = CLOUD_PROVIDER (menu_provider);
    gchar * path;

    GList * filelist = NULL;

    if (g_list_length(files) != 1)
        return NULL;

	file = thunarx_file_info_get_location(files->data);
	path = g_file_get_path(file);

    /*
     * D-Bus
     */

    DBusGConnection *connection;
    GError *error;
    DBusGProxy *proxy;
    //char **name_list;
    //int status;
    //char **name_list_ptr;
    gboolean in_cloud;
    gboolean syncing;

    error = NULL;
    connection = dbus_g_bus_get (DBUS_BUS_SESSION,
                                 &error);
    if (connection == NULL)
    {
        g_error_free (error);
        return NULL;
    }

    proxy = dbus_g_proxy_new_for_name (connection,
                                       "pt.meocloud.dbus",
                                       "/pt/meocloud/dbus",
                                       "pt.meocloud.dbus");

    error = NULL;
    if (!dbus_g_proxy_call (proxy, "FileInCloud", &error, G_TYPE_STRING,
                            path, G_TYPE_INVALID, G_TYPE_BOOLEAN,
                            &in_cloud, G_TYPE_BOOLEAN,
                            &syncing, G_TYPE_INVALID))
    {
        g_error_free (error);
        return NULL;
    }

    g_object_unref (proxy);

    if (!in_cloud)
        return NULL;

    action = g_object_new (GTK_TYPE_ACTION,
                           "name", "MEOCloud::open-in-browser",
                           "label", "Open in Browser",
                           "tooltip", "Open the selected file in a web browser",
                           NULL);
    g_object_set_qdata_full (G_OBJECT (action), "meocloud-selected-files",
                             thunarx_file_info_list_copy (files),
                             (GDestroyNotify) thunarx_file_info_list_free);
    g_object_set_qdata_full (G_OBJECT (action), "meocloud-provider",
                             g_object_ref (G_OBJECT (cloud_provider)),
                             (GDestroyNotify) g_object_unref);
    closure = g_cclosure_new_object (G_CALLBACK (cloud_open_in_browser), G_OBJECT (window));
    g_signal_connect_closure (G_OBJECT (action), "activate", closure, TRUE);
    actions = g_list_append (actions, action);

    if (g_file_test(path, G_FILE_TEST_IS_DIR)) {
        action = g_object_new (GTK_TYPE_ACTION,
                               "name", "MEOCloud::share-folder",
                               "label", "Share Folder",
                               "tooltip", "Share the selected folder",
                               NULL);
        g_object_set_qdata_full (G_OBJECT (action), "meocloud-selected-files",
                                 thunarx_file_info_list_copy (files),
                                 (GDestroyNotify) thunarx_file_info_list_free);
        g_object_set_qdata_full (G_OBJECT (action), "meocloud-provider",
                                 g_object_ref (G_OBJECT (cloud_provider)),
                                 (GDestroyNotify) g_object_unref);
        closure = g_cclosure_new_object (G_CALLBACK (cloud_share_folder), G_OBJECT (window));
        g_signal_connect_closure (G_OBJECT (action), "activate", closure, TRUE);
        actions = g_list_append (actions, action);
    } else {
        action = g_object_new (GTK_TYPE_ACTION,
                               "name", "MEOCloud::copy-link",
                               "label", "Copy Link",
                               "tooltip", "Copy a link to the selected file to your clipboard",
                               NULL);
        g_object_set_qdata_full (G_OBJECT (action), "meocloud-selected-files",
                                 thunarx_file_info_list_copy (files),
                                 (GDestroyNotify) thunarx_file_info_list_free);
        g_object_set_qdata_full (G_OBJECT (action), "meocloud-provider",
                                 g_object_ref (G_OBJECT (cloud_provider)),
                                 (GDestroyNotify) g_object_unref);
        closure = g_cclosure_new_object (G_CALLBACK (cloud_copy_link), G_OBJECT (window));
        g_signal_connect_closure (G_OBJECT (action), "activate", closure, TRUE);
        actions = g_list_append (actions, action);
    }

    return actions;
}
