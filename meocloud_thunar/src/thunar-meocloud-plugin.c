#include "cloud-provider.h"

static GType type_list[1];

G_MODULE_EXPORT void thunar_extension_initialize(ThunarxProviderPlugin * plugin)
{
    cloud_provider_register_type (plugin);
    type_list[0] = CLOUD_TYPE_PROVIDER;
    g_message("Initializing thunar-meocloud extension");
}

G_MODULE_EXPORT void thunar_extension_shutdown(void)
{
}

G_MODULE_EXPORT void thunar_extension_list_types(const GType ** types,
    gint * n_types)
{
    *types = type_list;
    *n_types = G_N_ELEMENTS(type_list);
}
