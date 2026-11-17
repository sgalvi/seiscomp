#ifndef SC_MAPVIEWX_PLUGIN_API_H
#define SC_MAPVIEWX_PLUGIN_API_H

#if defined(WIN32) && (defined(SC_MAPVIEWX_PLUGIN_SHARED) || defined(SC_ALL_SHARED))
# if defined(SC_MAPVIEWX_PLUGIN_EXPORTS)
#  define SC_MAPVIEWX_PLUGIN_API __declspec(dllexport)
#  define SC_MAPVIEWX_PLUGIN_TEMPLATE_EXPORT
# else
#  define SC_MAPVIEWX_PLUGIN_API __declspec(dllimport)
#  define SC_MAPVIEWX_PLUGIN_TEMPLATE_EXPORT extern
# endif
#else
# define SC_MAPVIEWX_PLUGIN_API
# define SC_MAPVIEWX_PLUGIN_TEMPLATE_EXPORT
#endif

#endif
