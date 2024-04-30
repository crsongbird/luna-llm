###    Luna.AI - Terminal Client    ###
#######################################
from openai import OpenAI
from enum import Enum
from datetime import datetime as dt
import json    # used by imported code
import getpass # is used by imported code
import subprocess
import textwrap
import os
from color import Color
from threading import Event

### maximum CPU threads
MAX_CPU_THREADS = 16
### maximum GPU ratio
MAX_GPU_RATIO = 0.225

# local OpenAI-compatible API
client = OpenAI(base_url="http://localhost:8899/v1", api_key="lm-studio")

class AppState:
    class __flags(Enum):
        # In powers of 2 so combined states may be used.
        AppInit = 1
        AppReset = 2
        Normal = 4
        GettingInput = 8
        Generating = 16
        ClientError = 32
        APIError = 64
        Quitting = 128
    # Clean ways to access flag values
    def AppInit(self) -> int:
        return self.__flags.AppInit.value
    def AppReset(self) -> int:
        return self.__flags.AppReset.value
    def Normal(self) -> int:
        return self.__flags.Normal.value
    def GettingInput(self) -> int:
        return self.__flags.GettingInput.value
    def Generating(self) -> int:
        return self.__flags.Generating.value
    def ClientError(self) -> int:
        return self.__flags.ClientError.value
    def APIError(self) -> int:
        return self.__flags.APIError.value
    def Quitting(self) -> int:
        return self.__flags.Quitting.value
    
    def __init__(self):
        # Initializes the state manager.
        self._state = AppState.__flags.AppInit
        print(f"Client set to initial state.")

    def get(self):
        # Returns the current state.
        return self._state.value
    
    def compare(self, compare_to) -> bool:
        # allows writing "if AppState.get(AppState.Normal()):"
        if self._state.value == compare_to:
            return True
        else:
            return False

    def set(self, state, verbose=False):
        # Sets the application state to the given value
        if isinstance(state, int):
            try:
                if verbose: print(f"{Color.gray}Setting state to: {state}{Color.reset}")
                self._state = AppState.__flags(state)
            except ValueError:
                print(f"{Color.red}Error:{Color.reset} Invalid app state value {state}. Using default state.")
                self._state = AppState.__flags.AppInit
        elif isinstance(state, str):
            try:
                if verbose: print(f"{Color.gray}Setting state to: {state}{Color.reset}")
                self._state = AppState.__flags[state]
            except KeyError:
                print(f"{Color.red}Error:{Color.reset} Invalid app state name '{state}'. Using default state.")
                self._state = AppState.__flags.AppInit
        else:
            print(f"{Color.red}Error:{Color.reset} Invalid input. Using default state.")
            self._state = AppState.__flags.AppInit

class Preferences:
    def __init__(self, alternative_persona = "luna"):
        # Optionally uses a supplied persona name
        self.persona = alternative_persona.lower()
        self.debug = False
        self.no_resize = False
        self.clear_console = 0
        self.console_lines = 100
        self.console_cols = 80
        
    def cls(self):
        # clears the screen only when the preference allows
        if self.clear_console == 1:
            os.system('cls' if os.name == 'nt' else 'clear')
            if self.debug:
                print(f"{Color.gray}The console was cleared. *** Set debug.opt to {Color.light_gray}False{Color.gray} to suppress this message!{Color.reset}")
        else:
            if self.debug:
                print(f"{Color.gray}A console clear was REFUSED due to user preference.{Color.reset}")
                
    def load(self):
        # loads preferences from disk
        print(f"{Color.yellow}Loading preferences...{Color.reset}")
        
        ### debug option
        with open("./meta/options/debug.opt", "r") as debug_file:
            self.debug = debug_file.read()
            if self.debug: print(f"{Color.gray}*** Debug mode is on. Expect verbose console output. ***{Color.reset}")
        
        ### no_resize option
        with open("./meta/options/no_resize.opt", "r") as no_resize_file:
            self.no_resize = no_resize_file.read()
            if self.debug: print(f"{Color.gray}no_resize value: {self.no_resize}{Color.reset}")
        
        ### console_clear option
        with open("./meta/options/clear_console.opt", "r") as console_clear_file:
            self.clear_console = console_clear_file.read()
            if self.debug: print(f"{Color.gray}clear_console value: {self.clear_console}{Color.reset}")
        
        ### console_lines option
        with open("./meta/options/lines.opt", "r") as console_lines_file:
            self.console_lines = console_lines_file.read()
            if self.debug: print(f"{Color.gray}console_lines value: {self.console_lines}{Color.reset}")
        
        ### console_cols option
        with open("./meta/options/cols.opt", "r") as console_cols_file:
            self.console_cols = console_cols_file.read()
            if self.debug: print(f"{Color.gray}console_cols value: {self.console_cols}{Color.reset}")
            if self.no_resize == False:
                os.system(f"mode CON: lines={self.console_lines} cols={self.console_cols}")
            else:
                if self.debug: print(f"{Color.gray}A console resize was REFUSED due to user preference.{Color.reset}")
        
        ### persona option
        with open("./meta/options/persona.opt", "r") as persona_file:
            self.persona = persona_file.read()
        
        ### all options loaded!
        print(f"{Color.light_cyan}All preferences loaded!{Color.reset}")
        Event().wait(0.25)
        print(f"{Color.yellow}Using persona: {Color.bold_text}{Color.cyan}\"{self.persona.title()}\"{Color.reset}{Color.yellow}!{Color.reset}")
        Event().wait(0.33)
        self.cls()

class MetaLuna:
    def __init__(self, user_preference_object : Preferences):
        # Default (fallback) attributes set here
        self.options = user_preference_object
        self.model_identifier = "model"
        self.system_message = f"You are {self.options}, an AI assistant running on of a terminal client."
        self.user_init_message = "Briefly explain who you are to a user opening this application for the first time."
        self.user_reset_message = "The user started a new chat. Your chat history has been cleared. Say hello!"
        self.initial_mod_string = "You are running on a console window on a user's computer. Keep your message to 20 words or less.\n*** (This message was generated by the moderator. The user cannot read it) ***"
        self.titlestr = "AI Terminal Application!"
        
        # Used to track whether this MetaLuna class owns the LM-Studio server process
        self.own_server = False
        self.model_loaded = False
        
        # Values for the current temp setting
        self.temperature = 0.8
        self.mode = "standard"
        
        # Command -> Temperature mappings
        self.temperature_map = {
            "mode:factual" : (0.3, "factual"),
            "mode:rational" : (0.5, "rational"),
            "mode:standard" : (0.8, "standard"),
            "mode:conversational" : (0.95, "conversational"),
            "mode:imaginative" : (1.3, "imaginative"),
            "mode:verbose" : (1.65, "verbose"),
        }
        
        # Commands which EXIT the model and the application.
        self.exit_commands = [
            f"{self.options.persona}:quit",
            f"{self.options.persona}:exit",
            f"{self.options.persona}:stop",
            f"bye, {self.options.persona}!",
            f"later, {self.options.persona}.",
            "quit",
            "exit",
            "stop",
            "qqq",
            "goodbye",
        ]
        
        # An array to store the chat history for the current session
        self.history = [{}]
        
    def load_file(self, filename):
        # Helper method to load files
        try:
            with open(filename, "r") as file:
                return file.read()
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
            return None
        
    def Init(self):
        # Initializes the model. Data is stored in a specific path structure.
        print(f"{Color.dark_green}Reading Model ID...{Color.reset}")
        Event().wait(0.25)
        self.model_identifier = self.load_file(f"./meta/{self.options.persona}/model-id")
        print(f"{Color.pink}Loading data for \"{self.model_identifier}\"...{Color.reset}")
        self.system_message = self.load_file(f"./meta/{self.options.persona}/system-short")
        self.user_init_message = self.load_file(f"./meta/{self.options.persona}/user-init")
        self.user_reset_message = self.load_file(f"./meta/{self.options.persona}/user-reset")
        self.initial_mod_string = eval(self.load_file(f"./meta/{self.options.persona}/init-mod-message"))
        self.titlestr = eval(self.load_file(f"./meta/{self.options.persona}/app-header"))
        Event().wait(0.333)
        
    def InitHistory(self):
        # Sets initial chat history for the first chat with Luna.
        self.history = [
            {"role": "system", "content": self.system_message},
            {"role": "assistant", "content": self.initial_mod_string},
            {"role": "user", "content": self.user_init_message},
        ]
        
    def ResetHistory(self):
        # Resets chat history when the user starts a new chat with Luna.
        self.history = [
            {"role": "system", "content": self.system_message},
            {"role": "assistant", "content": self.initial_mod_string},
            {"role": "user", "content": self.user_reset_message},
        ]
        
    def start_local_server(self):
        # a function to start the local lm-studio server and load the model from a MetaLuna class
        if self.own_server == False:
            try:
                subprocess.run(["lms", "server", "start"])
                self.own_server = True
            except subprocess.CalledProcessError:
                print("Local server is already running.")
                self.own_server = True
            # Load the model
            try:
                subprocess.run(["lms", "load", "--gpu", f"{MAX_GPU_RATIO}", self.model_identifier])
                self.model_loaded = True
            except subprocess.CalledProcessError:
                print(f"{Color.red}Model loading failed. Check if the model ID is correct.{Color.reset}")
                self.model_loaded = False
                
    def unload_local_server(self):
        # a function to unload the LLm from memory.
        if self.model_loaded:
            subprocess.run(["lms", "unload", self.model_identifier])

def main():
    ClientState = AppState()
    ClientOptions = Preferences()
    ClientOptions.load()
    LunaAI = MetaLuna(ClientOptions)
    while True:
        if ClientState.compare(ClientState.AppInit()):
            # Tests if an AppInit has been queued, resolves it.
            LunaAI.Init()
            LunaAI.InitHistory()
            LunaAI.start_local_server()
            ClientOptions.cls()
            ClientState.set(ClientState.Normal(), ClientOptions.debug)
            print(LunaAI.titlestr)
            
        if ClientState.compare(ClientState.Normal()) or ClientState.compare(ClientState.Quitting()):
            # Tests the various run conditions (including Quitting so the bot can say goodbye)
            completion = client.chat.completions.create(
                model=LunaAI.model_identifier,
                messages=LunaAI.history,
                temperature=LunaAI.temperature,
                stream=True,
                # Some extra kwargs that the Luna model supports
                extra_body={"max_tokens":"2048",
                            "top_k":"200",
                            "n_threads":f"{MAX_CPU_THREADS}"}
            )
            new_message = {"role": "assistant", "content": ""}
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    wrapped_output = textwrap.wrap(chunk.choices[0].delta.content)
                    print(Color.light_cyan + chunk.choices[0].delta.content + Color.reset, end="", flush=True)
                    new_message["content"] += chunk.choices[0].delta.content
            LunaAI.history.append(new_message)
            print()
            
            # Test if the Client State is quitting or some combo of Normal & Quitting before getting more user input
            if ClientState.compare(ClientState.Quitting()):
                LunaAI.unload_local_server()
                print(" *** Goodbye! ***\n", end="", flush=True)
                break
            
            # Get user input in light purple
            user_input = input(Color.light_purple + ">> ")
            print(Color.reset, end="", flush=True)
            
            # Process user commands
            if any(user_input.lower() == cmd for cmd in LunaAI.exit_commands):
                # The exit command was received
                print(f" << Command \"{user_input.lower()}\" received!\n", end="", flush=True)
                LunaAI.history.append({"role": "assistant", "content": "The user has chosen to exit the terminal application."})
                LunaAI.history.append({"role": "user", "content": "Goodbye."})
                ClientState.set(ClientState.Quitting(),ClientOptions.debug)
                
            elif user_input.lower() in LunaAI.temperature_map:
                # A mode change command was sent
                new_temp, mode = LunaAI.temperature_map[user_input.lower()]
                print(f" << Command \"{mode}\" received\n", end="", flush=True)
                LunaAI.history.append({"role": "assistant", "content": f"The user requested `{mode}` mode. The AI Temperature setting has changed to {new_temp:.2f}."})
                LunaAI.history.append({"role": "user", "content": f"Explain your `{mode}` mode to me in 12 words or less."})
                LunaAI.mode = mode
                LunaAI.temperature = new_temp
                
            elif user_input == "":
                # The user sent a blank message.
                LunaAI.history.append({"role": "user", "content": "(The user sent a blank message, indicating they would like you to continue your current thought.)"})
                
            else:
                # Append history with the current input
                LunaAI.history.append({"role": "user", "content": user_input})

if __name__ == "__main__":
    main()