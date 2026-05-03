from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class TradeFilters:
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    trade_setup: list[str] = field(default_factory=list)
    profitable: Optional[bool] = None
    side: Optional[str] = None
    tool_name: list[str] = field(default_factory=list)
    timeframe: list[str] = field(default_factory=list)

    @classmethod
    def from_request(cls, request) -> 'TradeFilters':
        params = request.query_params
        return cls(
            date_from=datetime.strptime(d, '%Y-%m-%d') if (d := params.get('date_from')) else None,
            date_to=datetime.strptime(d, '%Y-%m-%d') if (d := params.get('date_to')) else None,
            trade_setup=params.getlist('trade_setup'),
            profitable=p.lower() == 'true' if (p := params.get('profitable')) else None,
            side=params.get('side', '').upper() or None,
            tool_name=params.getlist('tool_name'),
            timeframe=params.getlist('timeframe'),
        )
