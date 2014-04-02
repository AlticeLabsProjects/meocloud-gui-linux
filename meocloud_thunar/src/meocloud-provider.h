#ifndef __MEOCLOUD_PROVIDER_H__
#define __MEOCLOUD_PROVIDER_H__

#include <thunarx/thunarx.h>

G_BEGIN_DECLS;

typedef struct _MEOCloudProviderClass MEOCloudProviderClass;
typedef struct _MEOCloudProvider MEOCloudProvider;

#define MEOCLOUD_TYPE_PROVIDER             (meocloud_provider_get_type())
#define MEOCLOUD_PROVIDER(obj)             (G_TYPE_CHECK_INSTANCE_CAST((obj),MEOCLOUD_TYPE_PROVIDER, MEOCloudProvider))
#define MEOCLOUD_PROVIDER_CLASS(klass)     (G_TYPE_CHECK_CLASS_CAST((klass), MEOCLOUD_TYPE_PROVIDER, MEOCloudProviderClass))
#define MEOCLOUD_IS_PROVIDER(obj)          (G_TYPE_CHECK_INSTANCE_TYPE((obj), MEOCLOUD_TYPE_PROVIDER))
#define MEOCLOUD_IS_PROVIDER_CLASS(klass)  (G_TYPE_CHECK_CLASS_TYPE((klass), MEOCLOUD_TYPE_PROVIDER))
#define MEOCLOUD_PROVIDER_GET_CLASS(obj)   (G_TYPE_INSTANCE_GET_CLASS((obj), MEOCLOUD_TYPE_PROVIDER, MEOCloudProviderClass))

GType meocloud_provider_get_type           (void) G_GNUC_CONST G_GNUC_INTERNAL;
void  meocloud_provider_register_type  (ThunarxProviderPlugin * plugin) G_GNUC_INTERNAL;

G_END_DECLS;

#endif
