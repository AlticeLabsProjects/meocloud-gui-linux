from gi.repository import Nautilus, GObject


class UpdateFileInfoAsync(Nautilus.InfoProvider, GObject.GObject):
    def __init__(self):
        pass

    def update_file_info(self, item):
        # test
        if "MEOCloud" in item.get_uri():
            item.add_emblem("emblem-ok-symbolic")

        return Nautilus.OperationResult.COMPLETE
