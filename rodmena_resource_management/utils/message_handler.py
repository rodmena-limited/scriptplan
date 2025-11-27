class MessageHandler:
    def error(self, id, message, source_file_info=None):
        print(f"ERROR: {message}")

    def warning(self, id, message, source_file_info=None):
        print(f"WARNING: {message}")
