
# Predefined ANSI escape sequences that will change the color of the console when injected into an F-string
class Color:
    gray = "\033[90m"  # Gray
    reset = "\033[0m"  # Reset to default color
    light_cyan = "\033[96m"  # Light cyan (used for chatbot output)
    light_purple = "\033[95m"  # Light purple (used for user input)
    red = "\033[91m"  # Red
    green = "\033[92m"  # Green
    yellow = "\033[93m"  # Yellow
    blue = "\033[94m"  # Blue
    magenta = "\033[95m"  # Magenta
    cyan = "\033[96m"  # Cyan
    white = "\033[97m"  # White
    purple = "\033[35m"  # Purple
    orange = "\033[33m"  # Orange
    dark_green = "\033[32m"  # Dark green
    dark_blue = "\033[34m"  # Dark blue
    pink = "\033[95m"  # Pink
    brown = "\033[33m"  # Brown
    light_gray = "\033[37m"  # Light gray
    dark_gray = "\033[90m"  # Dark gray
    black = "\033[30m"  # Black
    ### Styles
    bold_text = "\033[1m"  # Bold
    italic_text = "\033[3m"  # Italic
    underline_text = "\033[4m"  # Underline
    @staticmethod
    def rgb(r: int, g: int, b: int) -> str:
        """
        Generates an ANSI escape sequence for the specified RGB color.

        Args:
            r (int): Red component (0-255).
            g (int): Green component (0-255).
            b (int): Blue component (0-255).

        Returns:
            str: ANSI escape sequence for the specified RGB color.
        """
        if not (0 <= r <= 255) or not (0 <= g <= 255) or not (0 <= b <= 255):
            raise ValueError("RGB values must be in the range 0-255.")
        return f"\033[38;2;{r};{g};{b}m"