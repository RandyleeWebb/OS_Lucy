"""Stub audio processing — no-ops until real pipeline is wired."""

def loudnorm_normalize(path: str) -> None:
    pass

def mix_with_background(wav_path: str, bed_path: str) -> None:
    pass

def convert_to_mp2(wav_path: str, mp2_path: str) -> None:
    import shutil
    shutil.copy2(wav_path, mp2_path)
