class ShortTermMemory:
    def __init__(self):
        # We will store the titles of events here as they are read out loud
        self.last_spoken_events = [] 
        
# Create a single global instance that all modules can import and share
jarvis_cache = ShortTermMemory()