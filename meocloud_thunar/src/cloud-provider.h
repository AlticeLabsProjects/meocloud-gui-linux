#ifndef __CLOUD_PROVIDER_H__
#define __CLOUD_PROVIDER_H__

#include <thunarx/thunarx.h>

G_BEGIN_DECLS;

typedef struct _CloudProviderClass CloudProviderClass;
typedef struct _CloudProvider CloudProvider;

#define CLOUD_TYPE_PROVIDER             (cloud_provider_get_type())
#define CLOUD_PROVIDER(obj)             (G_TYPE_CHECK_INSTANCE_CAST((obj),CLOUD_TYPE_PROVIDER, CloudProvider))
#define CLOUD_PROVIDER_CLASS(klass)     (G_TYPE_CHECK_CLASS_CAST((klass), CLOUD_TYPE_PROVIDER, CloudProviderClass))
#define CLOUD_IS_PROVIDER(obj)          (G_TYPE_CHECK_INSTANCE_TYPE((obj), CLOUD_TYPE_PROVIDER))
#define CLOUD_IS_PROVIDER_CLASS(klass)  (G_TYPE_CHECK_CLASS_TYPE((klass), CLOUD_TYPE_PROVIDER))
#define CLOUD_PROVIDER_GET_CLASS(obj)   (G_TYPE_INSTANCE_GET_CLASS((obj),CLOUD_TYPE_PROVIDER, CloudProviderClass))

GType cloud_provider_get_type           (void) G_GNUC_CONST G_GNUC_INTERNAL;
void  cloud_provider_register_type  (ThunarxProviderPlugin * plugin) G_GNUC_INTERNAL;

G_END_DECLS;

#endif
