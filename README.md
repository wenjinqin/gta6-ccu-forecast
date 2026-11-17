# gta6-ccu-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/wenjinqin/gta6-ccu-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/wenjinqin/gta6-ccu-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

An empirical launch-curve forecaster for Grand Theft Auto VI's release day on Twitch. The program reads one case file — hour 1's viewer count plus the full hourly history of ~40 comparable game launches — and writes five quantiles (5/25/50/75/95%) for each of hours 2–24. For every comparable it builds the launch day's log-ratio curve against its own hour 1, then takes weighted empirical quantiles across the set: launches whose unlock pattern matches the target's (rolling midnight local vs a single global unlock) weigh more, the spread is calibrated on the four practice launches (Wolverine, RDR2, God of War Ragnarök, Spider-Man 2), and each level's curve is smoothed over a 3-hour window. On the practice cases it scores a mean log-pinball loss of ≈0.30 against the house baseline's ≈0.39. Pure Python 3 standard library, deterministic, no network.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/bounty/gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
