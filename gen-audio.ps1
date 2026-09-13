# Belt Runner audio generator: turns the clip list below into mp3 files in .\sfx via the ElevenLabs API.
# Sound effects use the sound-generation endpoint (loop=true for the continuous layers); voice lines use text-to-speech.
# The key is read from elevenlabs.key beside this script and never written anywhere else.
# Run:  powershell -ExecutionPolicy Bypass -File .\gen-audio.ps1
# Add -Only name1,name2 to regenerate just those clips; existing files are skipped unless -Force.
param([string[]]$Only=@(), [switch]$Force)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$key=(Get-Content (Join-Path $root 'elevenlabs.key') -Raw).Trim()
$out=Join-Path $root 'sfx'; New-Item -ItemType Directory -Force $out | Out-Null
# One voice for everything spoken in the game since 2026-09-13: the user's own "Nick Walkie Talkie Voice" clone (male,
# American, radio-flavoured). Both the controllers and Flight Ops use it; a clip's `voice` key can still override per line.
$VOICE_GAME='qJNvazAFWgdySz9n6ZlZ'
$VOICE_CONTROL=$VOICE_GAME   # the colony and approach controllers (was River SAz9YHcvj6GT2YYXdXww)
$VOICE_OPS=$VOICE_GAME       # Flight Ops, the tutorial voice (was Sarah EXAVITQu4vr4xnSDxMaL)
$clips=@(
  # --- continuous layers (seamless loops): the engine, the laser, the space hum
  @{name='engine_idle';   kind='sfx'; dur=4.0; loop=$true; text='spaceship engine idling, low steady hum with a soft turbine whir, seamless loop, no music'},
  @{name='engine_thrust'; kind='sfx'; dur=4.0; loop=$true; text='spaceship main engine under thrust, deep steady roar with an airy exhaust rush, seamless loop, no music'},
  @{name='engine_boost';  kind='sfx'; dur=4.0; loop=$true; text='spaceship afterburner at full cruise, huge deep rumbling roar with heavy sub bass, seamless loop'},
  @{name='retro';         kind='sfx'; dur=3.0; loop=$true; text='spaceship retro thrusters firing, steady hissing gas jet, seamless loop'},
  @{name='laser_beam';    kind='sfx'; dur=4.0; loop=$true; text='sci-fi mining laser beam sustained, deep pulsing throb with an electric buzz, seamless loop, no music'},
  @{name='laser_cut';     kind='sfx'; dur=4.0; loop=$true; text='laser beam cutting into rock, steady sizzling and crackling molten stone with sparks, seamless loop'},
  @{name='space_hum';     kind='sfx'; dur=6.0; loop=$true; text='very quiet deep space ambience, faint low rumble and a soft hull hum, seamless loop, no music'},
  # --- one-shots
  @{name='laser_on';   kind='sfx'; dur=1.0; text='sci-fi laser powering up, quick rising electric swell over a low thump'},
  @{name='laser_off';  kind='sfx'; dur=0.8; text='sci-fi laser powering down, short falling electric sigh'},
  @{name='laser_bite'; kind='sfx'; dur=0.7; text='laser beam striking rock, short sharp sizzling impact'},
  @{name='rock_break'; kind='sfx'; dur=1.8; text='large asteroid cracking apart in space, deep rocky crunch and crumbling debris'},
  @{name='radar_ping'; kind='sfx'; dur=1.5; text='clean bright sci-fi radar pulse ping with a soft fading echo'},
  @{name='zap';        kind='sfx'; dur=0.6; text='sci-fi energy bolt fired, short sharp electric zap'},
  @{name='hit';        kind='sfx'; dur=1.2; text='spaceship hull impact, heavy metallic thud with a rattle of loose plating'},
  @{name='boom';       kind='sfx'; dur=1.6; text='small spaceship explosion, sharp blast with scattering debris'},
  @{name='boom_big';   kind='sfx'; dur=3.0; text='huge explosion in space, deep booming blast with a long rumbling tail'},
  @{name='chime';      kind='sfx'; dur=1.0; text='soft sci-fi interface confirmation chime, two gentle bright notes'},
  @{name='pickup';     kind='sfx'; dur=0.6; text='small bright sci-fi pickup blip, quick ascending sparkle'},
  @{name='alarm';      kind='sfx'; dur=2.0; text='spaceship hull breach alarm, urgent repeating electronic klaxon'},
  @{name='click';      kind='sfx'; dur=0.5; text='soft short sci-fi interface click'},   # the API's minimum length is half a second
  @{name='warp_charge'; kind='sfx'; dur=4.5; text='huge spaceship warp drive charging up, deep rising electric hum building in power and pitch, sci-fi, no music'},
  @{name='warp_jump';   kind='sfx'; dur=2.5; text='massive starship jumping to warp, deep bass whoosh boom with a shimmering electric tail, sci-fi'},
  @{name='dock';        kind='sfx'; dur=2.2; text='heavy spaceship docking clamps locking with a deep metallic clunk and a hydraulic hiss, hangar interior'},
  @{name='stow';        kind='sfx'; dur=1.0; text='metal cargo crate sliding into a rack and latching, short mechanical clunk, sci-fi'},
  @{name='cash';        kind='sfx'; dur=1.5; text='futuristic cash register sale confirmation, pleasant two-note ascending chime, clean'},
  # --- no music here: the soundtrack is the game's own procedural synth engine; the API only makes sound effects and voices
  # --- voice lines
  @{name='colony_control';   kind='voice'; text='Colony control to cargo ship. You are cleared to hold station off Meridian. Welcome to the Hub.'},
  @{name='approach_control'; kind='voice'; text='Approach control has your ship. Stand by for docking.'},
  @{name='warp_ready';       kind='voice'; text='Jump drive charged. All hands, brace for warp.'},
  # --- tutorial: Flight Ops walks a new pilot through the first run (Sarah: mature, reassuring; a different voice from the controllers)
  @{name='tut_launch';   kind='voice'; voice=$VOICE_OPS; text='Welcome aboard, pilot. Flight Ops here. Approach control is taxiing you out of the hangar. Sit tight, and I will talk you through your first run.'},
  @{name='tut_steer';    kind='voice'; voice=$VOICE_OPS; text='You have the ship. The mouse steers. W and S work the throttle, A and D roll, and X cuts the throttle. Open her up and give me a turn.'},
  @{name='tut_hud';      kind='voice'; voice=$VOICE_OPS; text='Nicely done. Bottom centre is your ship: hull, fuel, speed, thrust and cargo. Top right is the world: your zone, the laser, the radar, and whatever you are looking at.'},
  @{name='tut_radar';    kind='voice'; voice=$VOICE_OPS; text='Press R to pulse the radar. Every rock it reaches gets marked for a while. Ore shows as coloured veins and crystals. Plain grey rock is barren, so do not waste the laser on it.'},
  @{name='tut_lock';     kind='voice'; voice=$VOICE_OPS; text='Find a copper rock, the orange veins, and put the mouse on it. Press Q to lock it. The target panel shows its size and how much is left in it.'},
  @{name='tut_mine';     kind='voice'; voice=$VOICE_OPS; text='Get within laser reach and hold the left mouse button. The dish under the nose cuts while you hold. When the rock breaks, fly through the glow and the ore comes aboard.'},
  @{name='tut_inv';      kind='voice'; voice=$VOICE_OPS; text='Copper in the hold. Press Tab for your inventory: four slots, one stack each. Drag a stack off the grid to jettison it if you ever need the room.'},
  @{name='tut_return';   kind='voice'; voice=$VOICE_OPS; text='Time to head home. Follow the cargo ship marker. Within two thousand two hundred fifty metres, press E and approach control brings you in.'},
  @{name='tut_hangar';   kind='voice'; voice=$VOICE_OPS; text='Docked. On the pad your tank fills from the cargo ship fuel supply, and your hull mends from its repair parts. Both run down, and both restock at the Hub.'},
  @{name='tut_stow';     kind='voice'; voice=$VOICE_OPS; text='Open the inventory and drag your copper down into the cargo ship storage. Fifty slots, and it all warps with you. Your hold is for the trip out, the storage is for the haul.'},
  @{name='tut_refit';    kind='voice'; voice=$VOICE_OPS; text='The services panel lists your refits. Laser, engine, tank, cargo, scanner and hull. A bigger hold and a stronger laser pay for themselves fastest. The cargo ship has its own upgrades below.'},
  @{name='tut_hub';      kind='voice'; voice=$VOICE_OPS; text='Nothing sells out here. Press N for the nav map, or use Warp to the Hub in the panel. Meridian Colony buys everything, and it is where the cargo ship refuels and restocks.'},
  @{name='tut_depart';   kind='voice'; voice=$VOICE_OPS; text='Press Depart, or W on the pad, to launch. Raiders roam the richer fields, and the laser cuts them too. If you ever run dry, T calls a tow.'},
  @{name='tut_done';     kind='voice'; voice=$VOICE_OPS; text='That is the loop. Fill the hold, stow it, warp to the Hub, sell, refit, repeat. Flight Ops out. Good hunting, pilot.'}
)
foreach ($c in $clips){
  if ($Only.Count -gt 0 -and $Only -notcontains $c.name) { continue }
  $file=Join-Path $out ($c.name+'.mp3')
  if ((Test-Path $file) -and -not $Force) { "skip  $($c.name) (exists)"; continue }
  try {
    if ($c.kind -eq 'sfx'){
      $b=@{text=$c.text; duration_seconds=$c.dur; prompt_influence=0.35}; if ($c.loop) { $b.loop=$true }
      $body=$b | ConvertTo-Json
      Invoke-WebRequest -Uri 'https://api.elevenlabs.io/v1/sound-generation' -Method Post -Headers @{'xi-api-key'=$key; 'Content-Type'='application/json'} -Body $body -OutFile $file | Out-Null
    } elseif ($c.kind -eq 'music'){
      $body=@{prompt=$c.text; music_length_ms=$c.ms} | ConvertTo-Json
      Invoke-WebRequest -Uri 'https://api.elevenlabs.io/v1/music' -Method Post -Headers @{'xi-api-key'=$key; 'Content-Type'='application/json'} -Body $body -OutFile $file -TimeoutSec 600 | Out-Null
    } else {
      # Delivery: slowed to 0.85x, a little less stability so the phrasing breathes, and a short pause after each sentence
      # (a <break> tag, which the multilingual v2 model honours) so the lines read like a person on a radio, not a ticker.
      $spoken=[regex]::Replace($c.text, '([.!?])\s+(?=\S)', '$1 <break time="0.5s" /> ')
      $body=@{text=$spoken; model_id='eleven_multilingual_v2'; voice_settings=@{stability=0.42; similarity_boost=0.8; style=0.1; use_speaker_boost=$true; speed=0.85}} | ConvertTo-Json -Depth 4
      $vid=if ($c.voice) { $c.voice } else { $VOICE_CONTROL }
      Invoke-WebRequest -Uri ("https://api.elevenlabs.io/v1/text-to-speech/$vid"+'?output_format=mp3_44100_96') -Method Post -Headers @{'xi-api-key'=$key; 'Content-Type'='application/json'; 'Accept'='audio/mpeg'} -Body $body -OutFile $file | Out-Null
    }
    "made  $($c.name)  $((Get-Item $file).Length) bytes"
  } catch {
    $detail=''; try { $rd=New-Object IO.StreamReader($_.Exception.Response.GetResponseStream()); $detail=' '+$rd.ReadToEnd() } catch {}   # the API's own explanation (quota, permissions, bad prompt)
    "FAIL  $($c.name): $($_.Exception.Message)$detail"
  }
}
