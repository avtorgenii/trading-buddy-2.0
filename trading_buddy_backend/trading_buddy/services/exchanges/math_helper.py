from decimal import Decimal, ROUND_DOWN
from typing import Tuple, List
from loguru import logger

import pytz
from datetime import datetime


def floor_to_digits(number: Decimal, digits: int) -> Decimal:
    quant = Decimal('1.' + '0' * digits)
    return number.quantize(quant, rounding=ROUND_DOWN)


def calc_position_volume_and_margin(
        deposit: Decimal,
        risk: Decimal,
        entry_p: Decimal,
        stop_p: Decimal,
        available_margin: Decimal,
        leverage: int,
        quantity_precision: int
) -> Tuple[Decimal, Decimal]:
    diff_pips = abs(entry_p - stop_p)

    allowed_loss = deposit * risk / 100

    volume = floor_to_digits(allowed_loss / diff_pips, quantity_precision)

    required_margin = volume * entry_p / leverage

    if available_margin >= required_margin:
        logger.debug(f"Margin required: {required_margin}")
        return volume, Decimal(round(required_margin, 2))
    else:
        allowed_volume = floor_to_digits(leverage * available_margin / entry_p, quantity_precision)
        logger.debug(f"Margin allowed: {allowed_volume * entry_p / leverage}")
        return allowed_volume, Decimal(round(allowed_volume * entry_p / leverage, 2))


def calculate_position_margin(entry_p: Decimal, volume: Decimal, leverage: int) -> Decimal:
    return Decimal(round(volume * entry_p / leverage, 2))


def calc_take_profits_volumes(
        volume: Decimal,
        quantity_precision: int,
        num_take_profits: int
) -> List[Decimal]:
    """
    Calculate the volumes for take profits.

    :param volume: Total volume to be distributed among take profits.
    :param quantity_precision: Precision for the volume.
    :param num_take_profits: Number of take profit targets.
    :return: List of volumes for take profits, largest volume first.
    """

    def round_with_precision(value, precision):
        factor = 10 ** precision
        return Decimal(round(value * factor) / factor)

    if num_take_profits <= 0:
        return []

    base_volume = Decimal(volume / num_take_profits)

    base_volume = round_with_precision(base_volume, quantity_precision)

    take_profits_volumes = [base_volume] * num_take_profits

    remaining_volume = Decimal(round_with_precision(volume - sum(take_profits_volumes), quantity_precision))

    # Adjust the first take profit volume to account for the remaining volume
    if remaining_volume != 0:
        take_profits_volumes[0] += remaining_volume

    # Sort volumes so the largest volume is first
    take_profits_volumes.sort(reverse=True)

    return take_profits_volumes


def calculate_position_potential_loss_and_profit(
        entry_p: Decimal,
        stop_p: Decimal,
        take_ps: List[Decimal],
        volume: Decimal,
        quantity_precision: int
) -> Tuple[Decimal, Decimal]:
    pot_loss = abs(entry_p - stop_p) * volume

    sum_of_weighted_prices = 0
    volumes = calc_take_profits_volumes(volume, quantity_precision, len(take_ps))

    if len(volumes) > 0:

        for exit_price, exit_volume in zip(take_ps, volumes):
            sum_of_weighted_prices += exit_price * exit_volume

        if volume == 0:
            return Decimal(0), Decimal(0)
        price_of_exit = sum_of_weighted_prices / volume

        pot_profit = abs(entry_p - price_of_exit) * volume
    else:
        pot_profit = Decimal(0)

    return floor_to_digits(pot_loss, 2), floor_to_digits(pot_profit, 2)


def convert_to_unix(utc_plus_2_string: str) -> int:
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
