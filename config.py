class BackgroundCleaner:
    sleepTime:int = 1  # seconds

class Language:
    defaultCode:str = "en"

class AssignmentModal:
    maxChars:int = 32

class NoteModal:
    class Question:
        maxChars:int = 32
    class Note:
        maxChars:int = 32

class Game:
    readyCountdown:int = 10  # seconds