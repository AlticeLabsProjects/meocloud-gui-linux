project(dolphin-meocloud-plugin)

FIND_PACKAGE( KDE4 REQUIRED )
FIND_PACKAGE(LibKonq REQUIRED)
INCLUDE( KDE4Defaults )

include_directories( ${QT_INCLUDES} ${KDE4_INCLUDES} ${LIBKONQ_INCLUDE_DIR} /usr/include/thrift)

kde4_add_plugin(dolphin-meocloud-plugin  shell_types.cpp shell_constants.cpp dolphin-meocloud-plugin.cpp)
target_link_libraries(dolphin-meocloud-plugin ${KDE4_KIO_LIBS} ${LIBKONQ_LIBRARY} thrift)

set (CMAKE_CXX_FLAGS "-fexceptions")

install(FILES dolphin-meocloud-plugin.desktop DESTINATION ${SERVICES_INSTALL_DIR})
install(TARGETS dolphin-meocloud-plugin DESTINATION ${PLUGIN_INSTALL_DIR})
