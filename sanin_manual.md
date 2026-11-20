# Sanin / Orochimaru - Complete User Manual and Troubleshooting Guide

Source-derived reference for the Sanin Android app (`ani.sanin`, source snapshot version `3.2.2`).

This manual is written for support and bot use. It covers the paths that exist in the current source, the actual player behavior, and the common failure cases. When code and old FAQ text disagree, trust the code-derived notes here.

## 0. The short version

- Sanin is a media player and tracker. It does not host anime, movies, TV, or subtitles.
- Streams come from installed extensions or add-ons, or from your own downloads.
- Anime tracking uses AniList or MAL. Anime catalogues can also come from extensions or native providers.
- Movie and TV tracking uses Simkl and metadata from TMDB.
- Movie and TV streams come from CloudStream sources and Stremio add-ons.
- The app has two main modes: Anime and Movie & TV. They do not use the same home screen, library, or player.
- The anime player is the full custom player. The Movie & TV player is a much simpler ExoPlayer screen.
- If video is black, the most useful fixes are usually, in this order: switch source/server, change Video output to TextureView, change Decoder to Hardware+ or Software, restart playback, then capture logs.
- Do not clear app data as a first step. It removes accounts, settings, and can make downloads harder to reach.
- The app has no working built-in app updater. Update the APK manually.
- The current source requires Android 7.0 or newer (`minSdk 24`). Old text claiming Android 5+ is outdated.

Do not share the Sanin GitHub repository or release URLs.

Samsung Tizen TVs and LG webOS TVs cannot install Android APKs. Use an Android TV box, Google TV device, Fire TV Stick, or another Android device.

## 1. Install and first launch

### Install

1. Get the latest APK from the official release channel.
2. Download the correct APK for your device.
3. On a phone or tablet, open the APK and allow install from that source if Android asks.
4. On Android TV or Fire TV, use Downloader or Send Files to TV to get the APK onto the device, then install it.
5. If an update will not install, try the legacy installer option in Extension Manager. This is intended for devices where the newer package installer fails.

Minimum Android version in the current source is Android 7.0 (API 24). The app targets Android 16 / API 36.

### First launch

- A splash screen appears first.
- On a fresh install, `FirstTimeProviderDialog` can appear once if `FirstTimeProviderShown` is false. It is a first-run provider prompt, not a source installer.
- The app starts in Anime mode by default.
- The default content source preference is Simkl, but Anime mode uses AniList or MAL for its catalogue/tracker depending on the selected tracker.
- Double-back exits the main screen.
- A foreground/incognito notification can appear while the app is active. Incognito still prevents progress updates.

### Main navigation

The main screen has four tabs:

- Home
- Explore
- Discover
- Library

The top bar shows the current mode, a Media Tracker button, Calendar, and the user avatar.

The right rail contains:

- Notifications
- Extensions
- Settings
- Providers
- Downloads
- Clear Cache
- Logout
- Media Tracker
- Avatar/profile

The mode card or mode label opens the Media Tracker sheet. This is where Anime and Movie & TV are selected.

## 2. Switching between Anime and Movie & TV

Open the Media Tracker sheet from the top bar or mode card.

### Anime

Expand Anime and choose:

- AniList
- MAL

The catalogue source can be:

- The selected tracker list, such as AniList or MAL.
- A native anime parser.
- An installed Aniyomi extension.

Anime mode then uses the Anime home, Anime discovery, Anime library, anime details, and the custom anime player.

### Movie & TV

Expand Movie & TV and choose:

- Simkl for tracking/list data.
- A metadata/catalogue source: `Simkl`, `All`, a CloudStream plugin, or a Stremio add-on.

Movie & TV mode then uses the TMDB/Simkl home, TMDB discovery, TMDB library, TMDB details, and the simpler Movie/TV player.

### Important distinction

The Movie & TV "source" in the Media Tracker sheet is usually a metadata/catalogue source. It is not the same as the playback server you choose later on the watch screen.

Anime streaming sources are chosen on the anime watch screen. Movie and TV playback sources are chosen from CloudStream plugins and Stremio add-ons on the TMDB watch screen.

### Rescue mode

If AniList is unreachable, the app can offer Rescue Mode with MAL. Rescue Mode changes the tracker so the app can keep working while AniList is down. Anime catalogue data may be limited in this mode.

Switch back to AniList from the Media Tracker sheet when AniList is available again.

## 3. Home

### Anime home

The anime home can show:

- Continue Watching
- Favorites
- Planned
- Missed
- Recommended
- Banner carousel
- Catalogue rows, depending on the selected catalogue source

Home sections can be reordered, shown, or hidden in Appearance. Some rows depend on being logged in. A logged-out user sees a call to action that opens the Accounts screen.

When the catalogue source is an extension or a native provider, the home rows come from that provider rather than only from AniList or MAL.

### Movie & TV home

The Movie & TV home uses Simkl and TMDB data. It can show:

- Banner carousel
- Simkl continue-watching and list sections
- Streaming-service rows
- Provider/company shelves
- Genre and discovery rows
- Trailer/reel rail
- A logged-out call to action that opens Accounts

If Movie & TV is empty, first check that you are in Movie & TV mode, that Simkl is connected if you expect personal rows, and that TMDB data is reachable.

## 4. Explore

### Anime Explore

Anime Explore is the catalogue/browse surface for Anime mode. Its rows depend on the selected tracker and catalogue source. If a row is empty, switch the anime catalogue source or refresh.

### Movie & TV Explore

Movie & TV Explore has three top selectors:

- Movie
- TV
- Animation

It can show:

- Trending banner
- Streaming services rail
- In Cinemas
- Trending
- Top Rated
- Latest Release
- Upcoming
- Franchise/collection cards
- Franchise search and sort

Animation uses TMDB animation genre data and can include both movie and TV animation.

Franchise cards are loaded separately. The row supports sorting, direction changes, search, and a collections/franchises mode.

## 5. Discover

### Anime Discover

Anime Discover includes:

- Curated Kitsu-based categories
- Category artwork
- Trailer/reel carousel
- Editorial shelves
- Category results with grid/list view
- Search entry
- Profile avatar shortcut

Category results load in pages. The trailer rail is a set of YouTube trailers, not full episodes.

### Movie & TV Discover

Movie & TV Discover includes:

- A large curated set of TMDB mood/trope/genre shelves
- Category artwork
- Trailer/reel rail
- Grid or list results
- All / Movie / TV filter inside a category
- Search entry
- Adult discovery content only when enabled

The shelf categories include psychological thrillers, mind-bending stories, heist films, detective stories, romance tropes, horror, science fiction, fantasy, animation, documentaries, regional cinema, and an Adult (NSFW) shelf.

If a category has no artwork, the app falls back to a placeholder. Missing artwork is not a playback problem.

## 6. Library

The Library uses the selected tracker and status tabs.

- Anime mode uses AniList or MAL lists.
- Movie & TV mode uses Simkl watched/list data and TMDB metadata.
- Status tabs include the usual watching/planning/completed style categories supported by the selected tracker.
- Sorting and filtering are available in the library UI.
- The profile/avatar area leads to user profile and activity surfaces.

If a title is missing from Library, check the selected tracker, whether the title is on the correct list, and whether the app is logged in.

## 7. Search

Search supports multiple source types:

- AniList
- MAL
- Kitsu
- Native anime parsers
- CloudStream sources
- Stremio sources

Search defaults to AniList only. Add more source chips to search more providers.

Search behavior:

- Results are grouped by source.
- Source chips show which providers are selected.
- Select All and Reset are available.
- Suggestions appear only when every selected search source is AniList or MAL.
- Suggestion requests are debounced.
- MAL suggestions require at least 3 characters.
- Search suggestions use a small recent cache.

Search filters include:

- Source
- Status
- Genres
- Excluded genres
- Tags
- Excluded tags
- Year
- Season
- Sort
- Adult only
- Country

Use Reset when a search returns nothing and you suspect old filters. In rescue mode, provider-specific filters are cleared so the fallback search can run.

If a title cannot be found in the tracker database, use the anime watch screen's Wrong Title? source search. That searches inside the selected source. This is the usual workaround for obscure or mismatched titles.

## 8. Media details

The details screen uses three main pills:

- Info
- Watch
- Comments

The third pill may be labeled Reviews in some places, but it opens the comments surface.

Info can include:

- Watch card
- Status and progress
- Airing countdown
- Description with show more
- Add to list / change status
- Favourite
- Share
- Trailer
- Opening/ending links
- Genres and tags
- External links
- Reviews/comments preview
- Characters
- Staff
- Recommendations
- Progress

Long-press behavior can copy titles, tags, or error text in some surfaces. The details screen is also where you choose the watch tab or comments tab.

## 9. Watching anime

### Source selection

On the anime watch screen you can see:

- Local downloads
- Native parsers
- Installed Aniyomi extensions
- Extension settings
- Dub/sub preference
- Download mode
- Refresh
- Source search / Wrong Title?
- WebView
- Subscribe
- Episode layout
- Sort
- FAQ

### Episode flow

1. Open a title.
2. Open Watch.
3. Pick a source.
4. Pick an episode or server.
5. The custom anime player opens.
6. Progress is saved according to the Progress settings.

If Smart Source Memory is enabled, the app can remember and preselect a source for new titles. If that remembered source is dead, the app can appear to open the wrong source or fail. Turn Smart Source Memory off or manually choose another source.

### Wrong Title?

Wrong Title? opens a search inside the selected source. Use it when the tracker title does not match the source title. It can also be used when AniList/MAL does not have the exact title you want to stream.

### Download mode

Download mode changes episode taps into download actions. Downloads appear in the Downloads screen and can be played from the Local downloads source.

### Anime player

The anime player is a fully custom ExoPlayer surface. It supports:

- Brightness and volume gesture sliders
- Double-tap seek
- Long-press speed
- Skip intro/outro
- Seek preview
- Speed control
- Rotate
- Brightness and volume buttons
- Resize/aspect ratio
- Audio track selection
- Subtitle track selection
- PiP
- Episode list
- Comments
- Source/quality switching
- Subtitle styling
- Playback speed
- Timestamp/skip controls

On TV, use the D-pad. Left/right seek, center plays or pauses, down opens track/audio/subtitle options. D-pad episode skipping can be enabled or disabled in player settings.

The anime player reads the Player Settings for decoder, video output, buffer, subtitles, and other behavior.

## 10. Watching movies and TV

### Source flow

1. Open Movie & TV mode.
2. Open a title.
3. Play Movie or choose an episode.
4. The watch screen lists CloudStream plugin sources and Stremio add-on sources.
5. Choose a server/source.
6. The Movie/TV player opens.

Movie & TV watch features include:

- Seasons and episodes
- Episode list styles
- Auto-continue
- Download mode UI
- Notifications
- Sort
- Server selection
- Auto-play mode
- Quality matching
- Refresh all
- Load-mode menu
- Make-default server behavior

### Critical player limitation

The Movie & TV player (`TmdbPlayerActivity`) is a simple ExoPlayer `PlayerView` with a back button. It does not have the anime player's gestures, subtitle styling, downloads, source switching, PiP, or custom decoder controls.

The Decoder and Video output settings apply to the anime player (`ExoplayerView`). They do not change the simple TMDB player.

Therefore, if a Movie or TV video is black, changing Decoder or Video output is not guaranteed to help. Switch the server or source first. If every server is black, the source/codec is the more likely problem.

## 11. Extensions, sources, and add-ons

### Where the paths actually are

The Settings root has six sections:

- Account
- Look & Feel
- Playback & App Behaviour
- Network & Data
- Downloads
- Utilities

Extension management is under:

`Settings > Utilities > Management > Extension Manager`

The Utilities Management screen is titled Extensions and contains:

- Extension Manager
- Add-ons
- Cache Manager
- Log Manager

The right-rail Extensions button opens the main extension browser.

### Extension modes

The Extensions screen has three modes:

- Aniyomi
- CloudStream
- Stremio

Use the mode toggle. Each mode has Installed and Available tabs.

### Aniyomi extensions

Aniyomi extensions are anime sources. Add a repository with either:

- A shortcode such as `username/repo/branch`
- A raw `index.min.json` URL

The app ships with a default Aniyomi repo and re-adds the anikoto repo if it is missing. Only add repositories you trust.

After adding a repo, install the extension, then return to the anime watch screen. The extension appears in the source list.

### CloudStream extensions

CloudStream sources are used mainly for Movie & TV playback, and can also appear in search.

CloudStream has no sites installed by default. If Movie & TV says there are no sources:

1. Open Extensions.
2. Switch the mode to CloudStream.
3. Open Available.
4. Add a trusted CloudStream repository.
5. Install one or more source extensions.
6. Return to the title and refresh.

CloudStream installed sources support reorder, update checks, per-source update, uninstall, and per-extension settings.

### Stremio add-ons

Stremio add-ons are managed in the Stremio mode of the Extensions screen. The Add-ons entry under Utilities is not the place to install Stremio add-ons.

Stremio sources can supply catalogs, metadata, streams, and subtitles. A Stremio add-on must support the relevant resource and media type. If it only provides catalogs, it will not provide playback streams.

The app includes a Stremio community add-on catalog endpoint and uses the `stremio:` source prefix internally.

### Add-ons screen

The Settings > Utilities > Management > Add-ons entry opens a legacy screen whose adapter is empty in the current source. Treat it as a dead/placeholder entry. Do not tell users to install streaming add-ons there.

### NSFW and adult content

There are several separate controls:

- NSFW on supported extensions: Extension Manager / extension settings.
- Hide Private Sources: Playback & App Behaviour.
- Adult Content: Playback & App Behaviour.
- Adult only in search filters.
- Include Adult Content in Discovery Shelves: Utilities > Management.
- Include NSFW titles inside Discover.

If an adult extension is installed but hidden, check all of these. The same content can be hidden by more than one switch.

### Extension troubleshooting

If an extension is missing:

- Confirm you are in the correct extension mode: Aniyomi for anime, CloudStream for Movie & TV.
- Confirm the extension is installed, not merely available.
- Check NSFW/hide-private toggles.
- Refresh the repository.
- Restart the app.
- Try a different repository.

If a repository will not load:

- Check the shortcode or raw index URL.
- Use a browser to confirm the URL returns JSON.
- Try a VPN or another DNS provider.
- A Cloudflare challenge can open a WebView. Complete it and retry.
- Update the app if the repository format changed.

If an extension installs but streams fail:

- Try another source/server.
- Update the extension.
- Open the extension's own settings.
- Some sources are region-blocked.
- Some sources are dead even though the extension is installed.

## 12. Downloads

Downloads are under `Settings > Downloads`.

### Storage

There are two storage modes:

- App storage: `Android/data/ani.sanin/files/Orochimaru/<series>/`
- Phone storage: a folder you choose with the system folder picker

If Phone storage is selected, you must choose a folder. The app creates series subfolders inside it.

Temporary downloads are written under the app cache and then committed to the final folder. Filenames are sanitized for filesystem safety.

Downloaded formats:

- M3U8/HLS downloads are remuxed into MKV.
- Direct MKV stays MKV.
- WebM stays WebM.
- Otherwise the final file is MP4.

### Queue settings

- Download only over Wi-Fi: waits for Wi-Fi.
- Concurrency: 1 to 10 episodes at once.
- Segments: 1 to 8 parallel range segments for direct downloads when the server supports ranges.
- Download progress notification.
- Completed notification.
- Auto-delete watched files: the switch exists, but the current source does not show a reliable consumer for it. Do not promise that it always deletes files.

### Downloads screen

The Downloads screen has queue and completed tabs, grouped series rows, pause/resume all, retry, play, delete, and clear-all actions.

If a download fails:

- Check free storage.
- Check the selected storage mode and folder permission.
- Turn off Wi-Fi-only or connect to Wi-Fi.
- Retry the item.
- Try fewer segments or lower concurrency.
- Try another source/server.
- HLS/DASH servers that do not expose usable segments can fail.
- Very large files can fail on constrained storage.

Clearing app cache is not the same as deleting downloads. Cache Manager clears cached media, Glide data, and ExoPlayer data.

## 13. Player settings and black video

### Exact path

`Settings > Playback & App Behaviour > Player & Sync > Player Settings`

The Player Settings screen has four tabs:

- Video
- Subtitle
- Playback
- Progress

### Video tab

Video tab includes:

- Prefer dub
- Buffer duration: 15, 30, 60, 90, 120 seconds
- Buffer memory limit: 64, 128, 192, 256 MB
- Pause overlay
- Wrap buttons style
- Gesture sliders
- Confirm player exit
- Pause on uninteraction
- Fast forward
- Double tap
- Seek time
- Seek sensitivity
- Skip time
- Default playback speed
- Picture in picture
- Decoder
- Video output

### Decoder values

- Hardware: only hardware-accelerated decoders. Fastest, but can fail on unsupported codecs or broken device decoders.
- Hardware+: hardware decoders first, then software fallback. Best first choice for most playback problems.
- Software: software decoding only. Most compatible, but slower and more CPU-heavy.

Behavior in code:

- Mode 0 filters to hardware-accelerated decoders only.
- Mode 1 tries hardware-accelerated decoders first and includes software decoders as fallback.
- Mode 2 filters to non-hardware/software decoders only.

Use Software for black video caused by an unsupported codec or a broken hardware decoder. Expect higher battery use and possible lag on high-resolution files.

### Video output values

- SurfaceView: fastest path. Some devices/overlays show black video with it.
- TextureView: composited output. It fixes black video on some devices, but costs more performance.

If video is black but audio and controls work, try TextureView before changing everything else.

### Subtitle renderer is separate

Subtitle Renderer is not the video renderer. It controls subtitle drawing:

- Canvas, often the TV default
- OpenGL, often the phone default

Changing the subtitle renderer will not fix black video. It can fix missing or badly drawn subtitles.

### Black video decision tree

Ask or determine:

1. Is this Anime or Movie & TV?
2. Do you hear audio?
3. Do the player controls appear?
4. Is it one title/source or every title?
5. Phone, tablet, Android TV, or Fire TV?
6. Did it start after changing decoder, video output, subtitles, or theme?

#### Anime, black video with audio and controls

Try in this order:

1. Switch to another server or source on the watch screen.
2. Try another quality, especially if the current one is HEVC, AV1, 10-bit, or HDR.
3. Open Player Settings > Video.
4. Set Video output to TextureView.
5. Set Decoder to Hardware+.
6. If still black, set Decoder to Software.
7. Back out and reopen the episode. If needed, force stop the app.
8. Clear Cache Manager, but do not clear app data.
9. Update the extension and the app.
10. Capture logs if it still fails.

#### Anime, black screen but no controls or UI

This is less likely to be a codec problem:

- Back out and reopen the player.
- Switch out of the player and back in.
- Check whether the app UI is also black. If the whole UI is black, change the app theme or disable an OLED/custom theme, then restart.
- If only the player surface is black, try TextureView and Software decoding.
- On TV, check the HDMI input, resolution, and whether the TV supports the output mode.

#### Movie & TV, black video

Remember that the simple TMDB player does not use the anime Decoder and Video output settings.

Try:

1. Switch to another server.
2. Switch to another CloudStream source or Stremio add-on.
3. Try a lower quality.
4. Refresh all servers.
5. Go back and re-open the title.
6. Try a different title with the same source to see whether the source is broken.
7. If every source is black, capture logs. This is usually source/codec/player limitation, not a setting the user can fix.

#### Black video with no audio

Check:

- The selected audio track.
- Whether the source is actually a video stream and not an audio-only or broken stream.
- The device volume and Bluetooth output.
- Decoder mode.
- Another server/source.

If subtitles appear over black video, the video track is decoding badly or is missing. Switch source first, then try decoder/output changes.

#### Green, purple, or corrupted video

This is usually a decoder or codec issue:

- Switch to Hardware+.
- If that fails, use Software.
- Try another quality/source.
- On old devices, avoid very high-bitrate HEVC/AV1 files.

#### Video freezes but audio continues

- Try Software decoding.
- Try another source/quality.
- Increase buffer duration and memory.
- Check device temperature and free RAM.

### What not to do first

- Do not clear app data.
- Do not uninstall all extensions immediately.
- Do not change DNS before trying another server.
- Do not tell Movie & TV users that the anime Decoder setting will definitely fix their player.

## 14. Audio and subtitle troubleshooting

### No audio

Check:

- Audio track selection in the player.
- Dub/sub preference.
- Device volume and output route.
- Bluetooth/headphones.
- Another server.
- Decoder mode.
- Whether the source has only a commentary or broken audio track.

If video plays but no audio works on any source, test another title and another device output.

### Audio out of sync

- Use the player's audio/subtitle sync controls if available.
- Switch server/source.
- Restart the episode.
- Try software decoding.
- Try a different quality.

### Subtitles missing

Check:

- Subtitles master toggle in Player Settings > Subtitle.
- A subtitle track is selected.
- Auto Download Subtitle.
- Online Providers: Wyzie, Stremio, OpenSubtitles.
- Online Language.
- Subtitle Renderer: Canvas or OpenGL.
- The source actually has subtitles.
- Stremio add-on supports subtitles.

### Subtitles badly rendered or invisible

- Switch Subtitle Renderer between Canvas and OpenGL.
- Change the font, size, color, outline, background, or alpha.
- Turn off experimental text-based subtitles if they break rendering.
- Try another subtitle track.

### Subtitles out of sync

- Use subtitle delay/sync controls.
- Use auto-sync if enabled.
- Try another subtitle track/provider.
- Try another source.

## 15. Accounts, tracking, and comments

### Accounts path

`Settings > Account > Accounts`

The account screen manages:

- AniList
- MAL
- Simkl

### AniList

AniList supports browser login and QR login.

Browser login opens:

`https://anilist.co/api/v2/oauth/authorize?client_id=45857&response_type=token&redirect_url=sanin://anilist`

If the browser does not return to the app, reopen Sanin and check the account state. If AniList is down, use Rescue Mode with MAL or wait.

### MAL

MAL is available after AniList is connected. The app notes that MAL support requires an AniList token. When both are connected, the app can keep MAL updated automatically.

Old media is not automatically back-synced to MAL just because you log in. Only new progress changes are reliably synced.

### Simkl

Simkl is used for Movie & TV tracking and personal rows. Connect it from the Accounts screen, then select Simkl in the Media Tracker sheet for Movie & TV.

### Comments

Comments settings are visible when AniList is connected.

Comment sources:

- Sanin comments
- Anikoto comments

The Sanin comments API is `https://api.dantotsu.app` when enabled. When disabled, the app points to localhost instead of making the request.

If comments do not load:

- Check AniList login.
- Check comment-source toggles.
- Check network/VPN/DNS.
- Try the other comment source.
- Some titles/episodes have no comments.

### AniList preferences

`Settings > Account > Accounts > AniList gear`

AniList settings can include:

- Score format
- Activity merge time
- Title language
- Staff name language
- AniList notification settings

These are server-side AniList preferences, not local display-only settings.

### Progress not syncing

Check:

- The correct tracker is selected.
- You are logged in.
- Progress Update mode: Always, Ask per title, or Never.
- Completion percentage.
- Incognito mode is off.
- The title is matched to the correct tracker entry.
- Network/API availability.

If progress is not updating after finishing an episode, open the title status control and check the progress prompt behavior. The old FAQ mentions long-press tricks, but current code should be treated as the source of truth.

## 16. Notifications and subscriptions

Path:

`Settings > Utilities > Alert Settings`

The screen covers:

- Master notification switch
- Subscription check interval
- View anime subscriptions
- View/remove TMDB subscriptions
- Import AniList lists/statuses into subscriptions
- Alarm rescheduling
- Battery optimization guidance

AniList notification worker interval options, in minutes:

`0, 30, 60, 120, 240, 360, 720, 1440`

Subscription worker interval options, in minutes:

`0, 480, 720, 1440`

`AlarmManagerScheduler` cancels schedules when notifications are disabled and refuses intervals under 15 minutes. Do not promise a 5-minute or 10-minute check.

If notifications do not arrive:

- Enable master notifications.
- Allow Android notifications for Sanin.
- Disable battery optimization for Sanin if the device aggressively kills background work.
- Check the interval.
- Check that the title is subscribed.
- Check AniList/Simkl connectivity.
- Re-save the subscription or reschedule alarms.

## 17. Appearance and performance

### Appearance

`Settings > Look & Feel > Appearance`

Appearance controls include:

- Theme
- Light/dark/system mode
- Accent palette
- OLED mode
- OLED intensity and gradient
- Custom theme
- Source-derived theme
- Material You
- UI scale
- Navigation style
- Cards and layout
- Banner style
- Glass/blur effects
- Home sections
- Live side rail

Theme notes:

- OLED mode only applies in dark mode.
- OLED modes are indexed 1 to 4 in the theme implementation.
- Accent palette includes a monochrome option at index 8.
- The default theme value is `BLUE`, but the theme manager falls back to `SANIN` for unrecognized values.
- Accent color 0 means the default Sanin accent.

### Motion

`Settings > Look & Feel > Motion`

Motion controls affect animations, transitions, and some player/UI effects. Disabling animations can make low-end devices feel faster.

### Performance checklist

If the app is slow:

1. Clear Cache Manager.
2. Turn off heavy glass/blur and reduce animation effects.
3. Lower buffer memory if the device is low on RAM.
4. Use Hardware+ or Hardware decoding for normal playback; use Software only when required.
5. Limit downloads concurrency.
6. Turn off logging when not troubleshooting.
7. Update the app and extensions.
8. Check free storage.
9. Avoid huge 4K/high-bitrate streams on weak devices.
10. Reduce home/discovery rows or artwork-heavy sections.

If playback stutters:

- Increase buffer duration to 60-120 seconds.
- Increase buffer memory to 128-256 MB only if RAM allows.
- Switch to a lower quality.
- Switch server.
- Try Hardware+.
- Check Wi-Fi and ISP throttling.
- Try a VPN if the source is being throttled.

## 18. Network, DNS, proxy, and backup

### Network & Data

`Settings > Network & Data > Connection & Backup`

Connection options:

- DNS Provider
- User Agent

DNS provider options include:

- None
- Cloudflare
- Google
- AdGuard
- Quad9
- AliDNS
- DNSPod
- 360
- Quad101
- Mullvad
- Controld
- Njalla
- Shecan
- Libre

Changing DNS restarts the app. DNS can help with blocked or failing domains, but it is not a general fix for dead sources.

### User Agent

User Agent is a custom HTTP identity string. Reset restores the default. A wrong User Agent can break some sources. Only change it when a source specifically requires it.

### Backup and restore

Export Settings saves a settings file to the downloads folder. The exported file is intended to contain General, UI, and Player preferences.

Import Settings accepts:

- `.sani`, encrypted with a password
- `.ani`, a legacy plain settings file

After a successful import, the app restarts. Export does not include accounts, downloads, or every possible preference.

### Proxy

Extension settings include a proxy setup and a SOCKS5 proxy dialog. Proxy settings are advanced. If a proxy is enabled and broken, sources and login can fail. Disable it when troubleshooting.

### Cloudflare

Some sources or logins open a WebView to complete a Cloudflare challenge. If a source fails with a Cloudflare page, complete the challenge and retry. If the WebView does not load, update Android System WebView or Chrome.

## 19. Logs and diagnostics

Path:

`Settings > Utilities > Management > Log Manager`

Log Manager contains:

- Master Logging
- View Live Logcat
- Capture Last 2 Minutes
- Clear Log Cache
- Share Log File

Steps to capture a useful log:

1. Open Log Manager.
2. Turn on Master Logging.
3. Go back and reproduce the problem.
4. Return to Log Manager.
5. Use Capture Last 2 Minutes or Share Log File.
6. Include the app version, device, mode, source, server, quality, and what you tapped.

The app can write a log file at external files `log.txt` when file logging is enabled. File logging is not the same as live logcat, and the Master Logging switch must be on for capture tools to be useful.

The version label at the bottom of Settings can be long-pressed to copy device information.

## 20. Android TV and Fire TV

- The app has TV-specific focus handling, larger navigation targets, and D-pad support.
- Player: left/right seeks, center plays or pauses, down opens track/audio/subtitle controls.
- Some player screens use a TV keyboard mode.
- Subtitle Renderer defaults differ between TV and phone.
- Focus may get stuck in a modal or sheet. Press Back to close the sheet, then navigate again.
- Fire TV installation is done with Downloader or a file-transfer app.
- Samsung Tizen and LG webOS TVs are not supported because they cannot install Android APKs.

If video is black on TV:

1. Switch source/server.
2. Set Video output to TextureView.
3. Set Decoder to Hardware+.
4. If needed, set Decoder to Software.
5. Check HDMI resolution and TV compatibility.
6. Test the same title on a phone to separate app/source problems from TV/HDMI problems.

## 21. Trailer reels

Discover has a trailer/reel rail.

- Trailers are YouTube videos embedded in a WebView.
- The rail is not a full episode source.
- Actions include play/pause, mute, seek, like/dislike locally, comments panel, share, and info.
- If a trailer is black, test YouTube in a browser and check WebView updates.
- Reels do not require a streaming extension, but they do require network access and TMDB/AniList data.

## 22. Common problems and fixes

### "No sources" or "No CloudStream sources installed"

- Add a CloudStream repository and install a source extension.
- Confirm you are in CloudStream mode, not Aniyomi.
- Return to the title and refresh.
- Add-ons are not streaming sources.

### Extension repository will not load

- Check URL/shortcode.
- Try a VPN or different DNS.
- Complete Cloudflare in the WebView.
- Update the app.
- Try another trusted repo.

### Extension installed but not visible

- Check the extension mode.
- Check NSFW and hide-private settings.
- Refresh the installed list.
- Restart the app.
- Confirm the extension is compatible.

### Search returns nothing

- Select more sources.
- Reset filters.
- Check adult-only filters.
- Try a different search source.
- Use Wrong Title? inside the watch screen.

### Anime list is empty

- Check AniList/MAL login.
- Check the selected tracker.
- Check the selected anime catalogue source.
- Check network and Rescue Mode.
- Refresh the screen.

### Movie & TV list is empty

- Check Simkl login.
- Check the selected Movie & TV metadata source.
- Check TMDB connectivity.
- Switch source to Simkl or All and refresh.

### Progress is not syncing

- Check tracker login.
- Check progress update mode.
- Check incognito mode.
- Check whether the title is matched correctly.
- Try updating progress manually once.

### Downloads fail or stop

- Check storage and folder permission.
- Disable Wi-Fi-only or connect to Wi-Fi.
- Retry.
- Lower concurrency/segments.
- Try another server.
- Check whether the server supports range requests.

### Notifications do not arrive

- Enable master notifications.
- Allow Android notifications.
- Disable battery optimization.
- Check interval and subscription.
- Check account/API connectivity.

### App is slow

- Clear cache.
- Reduce glass/blur and animations.
- Lower buffer memory.
- Limit downloads.
- Update app/extensions.
- Use a lower stream quality.

### App UI is black

- Change theme or disable OLED/custom theme.
- Restart the app.
- Check whether Material You or a source-derived theme caused it.
- If only the player is black, use the player troubleshooting steps.

### App crashes

- Capture the last 2 minutes of logs.
- Note what was open and which extension/source was used.
- Try safe mode or disable the most recently installed extension if the crash repeats.
- Update the app and extensions.

### Login fails

- Check AniList status.
- Try QR login instead of browser login.
- Reopen the app after browser auth.
- Check browser redirects.
- For MAL, connect AniList first.
- Disable a broken proxy/DNS/VPN.

### Comments do not load

- Check AniList login.
- Enable Sanin or Anikoto comments.
- Check network.
- Try another title/source.

### Trailer/reel is black

- Check WebView/Chrome updates.
- Test YouTube in a browser.
- Try another reel.
- Check network/VPN.

## 23. Source-derived limitations and caveats

- The app is not a manga/novel reader in the current UI, even though old strings and FAQs mention manga and light novels.
- `MediaType` only contains `ANIME`. Movie and TV are handled through TMDB/Simkl paths, not the anime media type.
- Add-ons under Settings > Utilities > Management > Add-ons is a placeholder/empty screen in the current source.
- The Settings > About screen exists in the manifest but has no launch reference found in the current settings UI. Do not give users an About path unless a build exposes it.
- `SettingsHomeActivity` also has no launch reference found. Treat it as hidden.
- The FAQ strings are old and mention manga, AniList-only behavior, and update checks that do not match the current app. Use the code-derived facts in this manual.
- The app has no working in-app app updater. `AppUpdater` is a no-op in both the Google and F-Droid flavors. Update the APK manually.
- `CheckUpdate` still matters for extension/plugin update checks. It is not an app installer.
- The Movie & TV player is intentionally basic. Do not describe it as having the anime player's features.
- Auto-delete watched downloads is exposed in settings but has no reliable consumer in the current source. Treat it as unreliable.
- Some strings and labels are legacy. If a label is not in the paths above, it may not be reachable in the current build.

## 24. Bot answer rules for Sanin support

When answering a random Sanin question:

1. Identify the mode first: Anime or Movie & TV.
2. Identify the device: phone/tablet or TV/Fire TV.
3. For playback, ask whether audio and controls work.
4. Give the smallest useful sequence, not a wall of settings.
5. Use exact paths from this manual.
6. For black video in Anime, recommend source/server first, then Video output > TextureView, then Decoder > Hardware+, then Software.
7. For black video in Movie & TV, do not promise the anime decoder settings will fix it. Recommend another server/source first.
8. Do not recommend clearing app data. Clear cache is acceptable when it is relevant.
9. Do not claim that Sanin hosts streams or subtitles.
10. Do not claim that Add-ons are streaming sources.
11. Do not claim that the app updates itself in-app.
12. If the user is on Samsung/LG TV, explain that Android APKs cannot be installed there.
13. If the problem is not solvable from settings, ask for Log Manager logs and the exact source/server/quality.
14. If a feature is not present in the current source, say so instead of inventing a path.
```
