import math
import pytz
from datetime import datetime


def floor_to_digits(number, digits):
    """
    Floor the number to a specified number of digits after the decimal point.

    :param number: The number to be floored.
    :type number: float
    :param digits: The number of digits to keep after the decimal point.
    :type digits: int
    :return: The floored number.
    :rtype: float
    """
    factor = 10 ** digits
    return math.floor(number * factor) / factor


def calc_position_volume_and_margin(deposit, risk, entry_p, stop_p, available_margin, leverage, quantity_precision):
    diff_pips = abs(entry_p - stop_p)

    allowed_loss = deposit * risk / 100

    volume = floor_to_digits(allowed_loss / diff_pips, quantity_precision)

    required_margin = volume * entry_p / leverage

    if available_margin >= required_margin:
        print(f"Required: {required_margin}")
        return volume, round(required_margin, 2)
    else:
        allowed_volume = floor_to_digits(leverage * available_margin / entry_p, quantity_precision)
        print(f"Allowed: {allowed_volume * entry_p / leverage}")
        return allowed_volume, round(allowed_volume * entry_p / leverage, 2)


def calc_take_profits_volumes(volume, quantity_precision, num_take_profits):
    """
    Calculate the volumes for take profits.

    :param volume: Total volume to be distributed among take profits.
    :param quantity_precision: Precision for the volume.
    :param num_take_profits: Number of take profit targets.
    :return: List of volumes for take profits, largest volume first.
    """

    def round_with_precision(value, precision):
        factor = 10 ** precision
        return round(value * factor) / factor

    base_volume = volume / num_take_profits

    base_volume = round_with_precision(base_volume, quantity_precision)

    take_profits_volumes = [base_volume] * num_take_profits

    remaining_volume = round_with_precision(volume - sum(take_profits_volumes), quantity_precision)

    # Adjust the first take profit volume to account for the remaining volume
    if remaining_volume != 0:
        take_profits_volumes[0] += remaining_volume

    # Sort volumes so the largest volume is first
    take_profits_volumes.sort(reverse=True)

    return take_profits_volumes


def calculate_position_potential_loss_and_profit(entry_p, stop_p, take_ps, volume, quantity_precision):
    volumes = calc_take_profits_volumes(volume, quantity_precision, len(take_ps))

    pot_loss = abs(entry_p - stop_p) * volume

    sum_of_weighted_prices = 0

    for exit_price, exit_volume in zip(take_ps, volumes):
        sum_of_weighted_prices += exit_price * exit_volume

    price_of_exit = sum_of_weighted_prices / volume

    pot_profit = abs(entry_p - price_of_exit) * volume

    return floor_to_digits(pot_loss, 2), floor_to_digits(pot_profit, 2)


def convert_to_unix(utc_plus_2_string):
    # Define the timezone
    utc_plus_2 = pytz.timezone('Etc/GMT-2')  # Etc/GMT-2 is equivalent to UTC+2

    # Parse the string into a datetime object
    local_time = datetime.strptime(utc_plus_2_string, '%Y-%m-%d %H:%M:%S')

    # Localize the datetime object to UTC+2
    local_time = utc_plus_2.localize(local_time)

    # Convert to UTC
    utc_time = local_time.astimezone(pytz.utc)

    # Convert to Unix timestamp
    unix_time = int(utc_time.timestamp())

    return unix_time
