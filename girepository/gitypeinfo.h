/* GObject introspection: Type
 *
 * Copyright (C) 2005 Matthias Clasen
 * Copyright (C) 2008,2009 Red Hat, Inc.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#ifndef __GITYPEINFO_H__
#define __GITYPEINFO_H__

#if !defined (__GIREPOSITORY_H_INSIDE__) && !defined (GI_COMPILATION)
#error "Only <girepository.h> can be included directly."
#endif

#include <gitypes.h>

G_BEGIN_DECLS

#define GI_IS_TYPE_INFO(info) \
    (g_base_info_get_type((GIBaseInfo*)info) ==  GI_INFO_TYPE_TYPE)

#define G_TYPE_TAG_IS_BASIC(tag) (tag < GI_TYPE_TAG_ARRAY || tag == GI_TYPE_TAG_UNICHAR)

const gchar*           g_type_tag_to_string            (GITypeTag   type);
const gchar*           g_info_type_to_string           (GIInfoType  type);

gboolean               g_type_info_is_pointer          (GITypeInfo *info);
GITypeTag              g_type_info_get_tag             (GITypeInfo *info);
GITypeInfo *           g_type_info_get_param_type      (GITypeInfo *info,
						        gint       n);
GIBaseInfo *           g_type_info_get_interface       (GITypeInfo *info);
gint                   g_type_info_get_array_length    (GITypeInfo *info);
gint                   g_type_info_get_array_fixed_size(GITypeInfo *info);
gboolean               g_type_info_is_zero_terminated  (GITypeInfo *info);
GIArrayType            g_type_info_get_array_type      (GITypeInfo *info);

G_END_DECLS


#endif  /* __GITYPEINFO_H__ */

