![image](https://github.com/mcorrigan/edit-as-you-go-sound-recorder/assets/1253843/dd02dcbc-b9a6-4181-858e-6c734946e308)

## Why This Tool?
Wrote this fairly quickly for my friend, Mason, who narrates awesome audio books. It takes him a lot of work to record himself and then edit the tracks. He also is not next usually next to the keyboard when he records.

This tool allows a person to record themselves in takes, and track all successful takes as they go. All this with audio queues so you don't have to see the screen to record. 

#### Contact Mason Willard - Stage, Film, and Voice Actor
- Soundcloud: [https://on.soundcloud.com/pw4a3](https://on.soundcloud.com/pw4a3)
- Youtube: [https://www.youtube.com/@_roscius](https://www.youtube.com/@_roscius)
- Email: mwillardpro@gmail.com 

## Audio Format
96kHz @ 32 Bit

This should be high enough quality for most recording, but you can change this with some simple changes in the code.

## Instructions
Before recording, choose session directory. This directory will be the location of one or two more directories after you finish recording your session (based on good/bad takes).

Next, choose your recording device or interface.

To begin recording, start the session (F10). Once the recording has started it is now recording audio. 
- When you are happy with the take, click Finish Good Take (F11). 
- If you don't like the take, click Finish Bad Take (F12). 
- If you are not sure about the take, click Replay Last Take and you can listen to the take on repeat, then choose Finish Good Take or Finish Bad Take. 

When you are done with the session, click End Session (F10). The last segment of recording prior to the session ending will be discarded.

Your good takes will all be in a folder called /recorder-keep and the rejected audio files are in a folder called /recorder-discard. All files have been named using timestamps so they are sortable. The location of these folders can be selected prior to starting a session. 

#### Keyboard Shortcuts
These can be changed in the code easily enough. The reason behind these was specific to the original use case of using a mini wireless keyboard to trigger recordings from inside the recording booth.

## Assembly in Audacity
For quick assembly in Audacity, you can select all your good takes and drag them into a new session. Next, select them all and choose Tracks from the top menu. Then choose Align Tracks -> Align End to End.

![image](https://github.com/mcorrigan/edit-as-you-go-sound-recorder/assets/1253843/3c645d7e-7419-463c-8d2f-2d872a518758)

Also, it may be helpful to turn on ripple edit so as you modify each take, the other audio files don't fall behind. You can enable this by going to Edit -> Preferences and the go to Track Behaviors and check the box "Editing a clip can move other clips"

![image](https://github.com/mcorrigan/edit-as-you-go-sound-recorder/assets/1253843/de18d3b0-2a97-4ef9-98b1-a2fdc017d073)


## More Help or Desired Changes
The code is available as is. If you find bugs, please submit them on Github and I will address them as I am able and time permits. In the event you would like bugs fixed sooner, customizations, or personal help setting up and using the program, I can be available to help for $150 / hr. Leave an issue with your email to contact me.
