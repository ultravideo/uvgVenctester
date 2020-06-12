* **Well documented**
* General
  * **Well documented**
  * Equal support for Windows and Linux
  * Simple and well documented enough for people to use/maintain/tweak with ease
  * Python 3.6 >=
    * Must use type hinting for function parameters and return values
    * Modules
      * Pathlib
      * Pandas
      * Numpy
      * Matplotlib
  * Distribute tasks
* Running tests
  * Input files from glob syntax (Pathlib)
  * Configurable QP, bitrate, bitrate scaled by resolution, or BPP lists
  * Warmup functionality
  * Specify number of samples to measure encoding time (and bitrate and distortion)
  * Ability to specify order of tests
  * Ability to specify how many instances are run in parallel 
  * Choose whether or not save encoded and decoded files
  * Reuse old results unless specified otherwise
  * Support for multipass encoding
  * Multiple different inputs with same test parameters
* Usability
  * Test cases are easily programmatically generatable
  * Progress bar / output how many encodings have been completed
  * Selecting anchor individually for each test case possible but if not defined automatic anchor selection
  * Changing settings that don't actually change the preset shouldn't generate new test case, e.g., test cases set to `--preset ultrafast` and `--preset ultrafast --no-smp` generates only one test case or if the other one is already ran once do not run it again
  * Similarly changing the order of the parameters should not cause multiple different test cases
    * Take care of parameters where order matters, hold the users hand, if somebody writes `--me hexbs --preset veryslow` they probably meant `--preset veryslow --me hexbs`
       * Currently only parameters I know that touch others are `--preset` and `--gop` (touches `--intra-bits` and `--clip-neighbour`) (Joose 2020-05-06)
  * **Well documented**
  * An easy way to set bitrate at a sequence level
* Weekly tests
  * First stage, simple and reliable tables
* Results
  * CSV or other simple excel compatible format
  * BD-BR, absolutely must match JCT-VC excel sheet (highest priority)
  * [BSQ](https://www.researchgate.net/publication/340060891_BSQ-rate_a_new_approach_for_video-codec_performance_comparison_and_drawbacks_of_current_solutions)
  * Image quality metrics
    * Primary
      * YUV-PSNR
      * YUV-SSIM
    * Secondary
      * VMAF
      * MS-SSIM
  * Per sequence
    * Encoder
    * Anchor
    * Used parameters
    * Sequence name
    * Sequence frame count
    * Bitrate
    * Quality parameter (QP, bitrate, BPP)
    * Encoding time
    * Speedup
  * Plot RD-curves and speedup curves
  * Generate summary table from results (DataFrame/csv/...)
    * Has to be understandable by Jarno in three seconds
  * Easy/extencible way to define new/custom summaries
    * Separate from testing functionality (i.e. no need to dig around testing code to define new summary generation)
    * Well documented interface for passing test data to summary generation
    * Summary definitions passed as parameters (i.e. not a separate function for each kind of summary)
* Encoders
  * Primary
    * Kvazaar (HEVC and VVC)
    * HM and VTM
    * x265
  * Secondary
    * SVT-HEVC
    * Turing
  * **Well documented**
* Building
  * Get rid of Scons?
    * We should probably use original make/project files and not create our own
    * No one currently has really experience with scons
    * Does it really solve any problem, but just adds one more thing to maintain?
  * Support building from git (at least Kvazaar)
  * Support copying manually built executable
  * Support adding defines when compiling
    * Framework should also realize that different defines means different executable
* Git
  * Option to auto-fetch remotes
  * Select version by hash/branch/tag
* No unnecessary writing of files to disk
* **Well documented**