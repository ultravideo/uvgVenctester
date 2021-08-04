from tester.core.cfg import Cfg
Cfg().tester_sequences_dir_path = r"/test_seqs"
Cfg().tester_binaries_dir_path = "/binaries"
Cfg().tester_output_dir_path = "/encodes"
Cfg().tester_sources_dir_path = "/source"

Cfg().kvazaar_remote_url = r"https://github.com/ultravideo/kvazaar.git"

# TODO: build HM in Dockerfile
# Cfg().hevc_reference_decoder = r"TAppDecoder"

Cfg().vmaf_repo_path = r"/usr/src/app/vmaf"