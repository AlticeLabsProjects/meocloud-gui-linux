# Check http://elementaryos.org/docs/developer-guide/cmake for documentation

cmake_minimum_required (VERSION 2.8)
cmake_policy(VERSION 2.8)

project(Marlin-MEOCloud)

list(APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake)

# Vala stuff
find_package(Vala REQUIRED)
include(ValaVersion)
ensure_vala_version("0.12.0" MINIMUM)
include(ValaPrecompile)

vala_precompile(VALA_C marlin-meocloud
    plugin.vala
PACKAGES
    gtk+-3.0
    gio-2.0
    marlincore
OPTIONS
    --thread
    --vapidir=${CMAKE_SOURCE_DIR}/vapi
)

# C stuff
find_package(PkgConfig)
pkg_check_modules(DEPS REQUIRED
    gtk+-3.0
    gio-2.0
    marlincore
)
set(CFLAGS
    ${DEPS_CFLAGS} ${DEPS_CFLAGS_OTHER}
)
set(LIB_PATHS
    ${DEPS_LIBRARY_DIRS}
)
link_directories(${LIB_PATHS})
add_definitions(${CFLAGS})

add_library(marlin-meocloud SHARED ${VALA_C})
target_link_libraries(marlin-meocloud marlincore ${DEPS_LIBRARIES})

install(FILES meocloud.plug DESTINATION lib/pantheon-files/plugins/)
install(TARGETS marlin-meocloud DESTINATION lib/pantheon-files/plugins/)
