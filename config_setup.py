from getpass import getpass

import yaml
import click
import openai
from enum import Enum, auto
from typing import Callable
from openai.error import AuthenticationError
from constants import CONFIG_PATH, API_KEY_PATH


class AvailableModels(Enum):
    TEXT_ADA_001 = auto()
    TEXT_BABBAGE_001 = auto()
    TEXT_CURIE_001 = auto()
    TEXT_DAVINCI_003 = auto()

    @classmethod
    def as_list(cls) -> list:
        return list(map(lambda c: c.name.replace("_", "-").lower(), cls))


class SetupHelper:
    def __init__(self):
        self._api_key = None
        self._model = None
        self._num_answers = None
        self._max_tokens = None
        self._temperature = None
        self._top_p = None
        self._frequency_penalty = None
        self._presence_penalty = None

    @staticmethod
    def print_logo():
        click.echo("\n"
                   "██████████   ██████████   ███   ███  ██████████   ███\n"
                   "███    ███   ███    ███   ███  ███   ███    ███\n"
                   "███    ███   ███    ███   ███  ███   ███    ███\n"
                   "███    ███   ███    ███   ███▐███    ███    ███    ▄█\n"
                   "███    ███   ███          █████▀     ███    ███   ███\n"
                   "██████████   ██████████   █████      ██████████   ███▌\n"
                   "███    ███          ███   ███▐███    ███    ███   ███▌\n"
                   "███    ███          ███   ███  ███   ███    ███   ███\n"
                   "███    ███   ██████████   ███   ███  ███    ███   █▀\n"
                   "\n"
                   "    ~~~~~~~ Your simple terminal helper ~~~~~~~\n")

    def user_input_api_key(self, max_tries: int = 3):
        if API_KEY_PATH.is_file():
            click.echo("NOTE: You've already added a key. This old key will be overwritten in this setup!\n")

        click.echo("To use the CLI, please enter your OpenAI API key. The key can be generated by \n"
              "creating an account at https://openai.com/api/\n"
              "\n"
              "The key will only be stored locally in `~/.askai/key`.\n")
        key = getpass("Enter API Key: ")
        num_tries = 1

        while not _is_valid_api_key(key):
            if num_tries >= max_tries:
                click.echo(click.style("Too many invalid tries. Aborted!", fg="red"))
                exit(1)
            click.echo(click.style("The API key is not valid.", fg="red"))
            key = getpass("Enter API Key: ")
            num_tries += 1

        self._api_key = key

    @staticmethod
    def print_update_config_note() -> None:
        click.echo("NOTE: You're about to update the default config of askai. This will have an effect on \n"
              "how the answers are generated. Make sure that you are well-informed around these effects. \n"
              "You can read more here: https://beta.openai.com/docs/api-reference/completions/create")
        click.echo()

    def user_input_model(self, step_num: int, max_tries: int = 3):
        click.echo(f"-> STEP {step_num} - SET MODEL")
        for idx, model_name in enumerate(AvailableModels.as_list()):
            click.echo(f"   {idx+1}) {model_name}")
        model = input("Choose model (1-4): ")
        num_of_tries = 1

        while not _is_int(model) or int(model) not in range(1, 5):
            if num_of_tries >= max_tries:
                click.echo(click.style("Too many invalid tries. Aborted!", fg="red"))
                exit(1)

            click.echo(click.style("Choose value between 1 and 4.", fg="red"))
            model = input("Choose model (1-4): ")
            num_of_tries += 1

        self._model = AvailableModels(int(model)).name.replace("_", "-").lower()
        click.echo(click.style(f"Model chosen: {self._model}", fg="green"))
        click.echo()

    def user_input_num_answers(self, step_num: int, max_tries: int = 3):
        self._num_answers = self._user_input_integer(
            input_text=f"-> STEP {step_num} - SET NUMBER OF ALTERNATIVE ANSWERS GENERATED PER QUESTION\n"
                       "   This is the number of answers that will be displayed when you ask \n"
                       "   a question. A high number will use more tokens.\n"
                       "   Allowed values: >0\n"
                       "Choose number of answers (press enter for default = 1): ",
            default=1,
            predicate=lambda x: x > 0,
            max_tries=max_tries
        )

    def user_input_max_token(self, step_num: int, max_tries: int = 3):
        self._max_tokens = self._user_input_integer(
            input_text=f"-> STEP {step_num} - SET MAXIMUM NUMBER OF TOKENS\n"
                       "   A too low number might cut your answers shortly.\n"
                       "   Allowed values: >0\n"
                       "Choose maximum number of tokens (press enter for default = 300): ",
            default=300,
            predicate=lambda x: x > 0,
            max_tries=max_tries
        )

    def user_input_temperature(self, step_num: int, max_tries: int = 3):
        self._temperature = self._user_input_float(
            input_text=f"-> STEP {step_num} - SET TEMPERATURE\n"
                       "   Sampling temperature to use. Higher values means \n"
                       "   the model will take more risks. Try 0.9 for more \n"
                       "   creative applications, and 0 for ones with a well-defined \n"
                       "   answer.\n"
                       "   Allowed values: 0.0 <= temperature <= 1.0\n"
                       "Choose temperature (press enter for default = 0.4): ",
            default=0.4,
            predicate=lambda x: 0.0 <= x <= 1.0,
            max_tries=max_tries
        )

    def user_input_top_p(self, step_num: int, max_tries: int = 3):
        self._top_p = self._user_input_float(
            input_text=f"-> STEP {step_num} - SET TOP_P\n"
                       "   An alternative to sampling with temperature, called \n"
                       "   nucleus sampling, where the model considers the results \n"
                       "   of the tokens with top_p probability mass. So 0.1 means \n"
                       "   only the tokens comprising the top 10% probability mass \n"
                       "   are considered.\n"
                       "   It's generally recommend altering this or temperature, but not both!"
                       "   Allowed values: 0.0 <= top_p <= 1.0\n"
                       "Choose top_p (press enter for default = 0.0): ",
            default=0.0,
            predicate=lambda x: 0.0 <= x <= 1.0,
            max_tries=max_tries
        )

    def user_input_frequency_penalty(self, step_num: int, max_tries: int = 3):
        self._frequency_penalty = self._user_input_float(
            input_text=f"-> STEP {step_num} - SET FREQUENCY PENALTY\n"
                       "   Positive values penalize new tokens based on their existing \n"
                       "   frequency in the text so far, decreasing the model's likelihood \n"
                       "   to repeat the same line verbatim."
                       "   Allowed values: -2.0 <= frequency penalty <= 2.0\n"
                       "Choose frequency penalty (press enter for default = 0.0): ",
            default=0.0,
            predicate=lambda x: -2.0 <= x <= 2.0,
            max_tries=max_tries
        )

    def user_input_presence_penalty(self, step_num: int, max_tries: int = 3):
        self._presence_penalty = self._user_input_float(
            input_text=f"-> STEP {step_num} - SET PRESENCE PENALTY\n"
                       "   Positive values penalize new tokens based on whether they appear \n"
                       "   in the text so far, increasing the model's likelihood to talk about \n"
                       "   new topics."
                       "   Allowed values: -2.0 <= presence penalty <= 2.0\n"
                       "Choose presence penalty (press enter for default = 0.0): ",
            default=0.0,
            predicate=lambda x: -2.0 <= x <= 2.0,
            max_tries=max_tries
        )

    def save_api_key(self):
        API_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        API_KEY_PATH.write_text(self._api_key)
        click.echo(click.style("Your API key has been successfully added!", fg="green"))

    def save_config(self):
        config = {
            "model": self._model,
            "num_answers": self._num_answers,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "top_p": self._top_p,
            "frequency_penalty": self._frequency_penalty,
            "presence_penalty": self._presence_penalty,
        }

        with open(CONFIG_PATH, "w") as f:
            yaml.dump(config, f)

        click.echo(click.style("Config saved successfully!", fg="green"))

    @staticmethod
    def _user_input_integer(input_text: str,
                            default: int,
                            predicate: Callable[[int], bool] = lambda x: True,
                            max_tries: int = 3) -> int:
        for _ in range(max_tries):
            input_value = input(input_text)

            if input_value == "":
                click.echo(click.style(f"Value chosen: {default}", fg="green"))
                click.echo()
                return default

            if not _is_int(input_value):
                click.echo(click.style("Input is not an integer.\n", fg="red"))
                continue
            elif not predicate(int(input_value)):
                click.echo(click.style("Input is not within allowed range.\n", fg="red"))
                continue

            click.echo(click.style(f"Value chosen: {input_value}", fg="green"))
            click.echo()
            return int(input_value)

        click.echo(click.style("Too many invalid tries. Aborted!", fg="red"))
        exit(1)

    @staticmethod
    def _user_input_float(input_text: str,
                          default: float,
                          predicate: Callable[[float], bool] = lambda x: True,
                          max_tries: int = 3) -> float:
        for _ in range(max_tries):
            input_value = input(input_text)

            if input_value == "":
                click.echo(click.style(f"Value chosen: {default}", fg="green"))
                click.echo()
                return default

            if not _is_float(input_value):
                click.echo("Input is not a float.\n")
                continue
            elif not predicate(float(input_value)):
                click.echo("Input is not within allowed range.\n")
                continue

            click.echo(click.style(f"Value chosen: {input_value}", fg="green"))
            click.echo()
            return float(input_value)

        click.echo(click.style("Too many invalid tries. Aborted!", fg="red"))
        exit(1)


def _is_valid_api_key(key: str) -> bool:
    openai.api_key = key
    try:
        # Use free `content-filter-alpha` endpoint to check if API key is valid.
        openai.Completion.create(model="content-filter-alpha")
        return True
    except AuthenticationError:
        return False


def _is_int(x):
    try:
        int(x)
        return True
    except ValueError:
        return False


def _is_float(x):
    try:
        float(x)
        return True
    except ValueError:
        return False

