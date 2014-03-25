namespace py shell
namespace cpp Shell
namespace cocoa MCLD

enum NotificationType {
    FILE_STATUS
}

enum FileState {
    READY
    SYNCING
    IGNORED
    ERROR
}

enum MessageType {
    SUBSCRIBE_PATH
    SHARE
    OPEN
    FILE_STATUS
}

enum SubscribeType {
    SUBSCRIBE
    UNSUBSCRIBE
}

enum ShareType {
    LINK
    FOLDER
}

enum OpenType {
    BROWSER
}

enum FileStatusType {
    REQUEST
    RESPONSE
    MULTI_REQUEST
    MULTI_RESPONSE
}

struct SubscribeMessage {
    1: SubscribeType type,
    2: string path,
}

struct ShareMessage {
    1: ShareType type,
    2: string path,
}

struct OpenMessage {
    1: OpenType type,
    2: string path,
}

struct FileStatus {
    1: string path,
    2: FileState state,
}

struct FileStatusMessage {
    1: FileStatusType type,
    2: optional FileStatus status,
    3: optional list<FileStatus> statuses,
}

struct Message {
    1: MessageType type,
    2: optional SubscribeMessage subscribe,
    3: optional ShareMessage share,
    4: optional OpenMessage open,
    5: optional FileStatusMessage fileStatus,
}
