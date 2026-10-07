
## Photos that slide over the map
- images.json lists photos per scene (use the scene's exact title). Two kinds: {"commons": "File:Name.jpg"} is looked up on Wikimedia Commons,
  REFUSED unless its licence allows reuse (public domain, CC0, CC BY, CC BY-SA), and credited automatically; {"file": "photos/x.jpg", "credit": "Photo: Name"}
  is your own photo or one you have permission for (a credit line is required).
- Cards slide in from the right or from the bottom ("slide": "right" | "bottom" | "alternate"), show a caption and the credit, and the credits
  are appended to the description file. Several photos in one scene take turns.
- Find candidates: Actions > "Find free photos (Wikimedia Commons)" > download image_candidates.html > pick calm photos of places and memorials.
  No victims or graphic scenes. Archive photos of the events (ICRC, Eritrean Red Cross, NFB, press agencies) are normally NOT free: ask for permission.

## Your song
- song.mp3 (your recording, with vocals) plays alone for the first and last ~14 seconds; a quiet vocal-free bed plays under the narration.
- music.mp3 (instrumental only) instead plays under the whole video. Lower or raise it with BED_LEVEL.
- remove_vocals.py (also an Actions workflow) tries to strip vocals with an AI model. On a recording that is mostly voice it leaves almost nothing.
