import os
import io
import time
from nemo.collections.asr.models import EncDecRNNTBPEModel
import os
from colorama import Fore
import numpy as np
import torch
from pydub import AudioSegment


class LingoAPIModelB:
    def __init__(self):

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.MODEL_NAME = "nvidia/parakeet-rnnt-0.6b"

        self.model = EncDecRNNTBPEModel.from_pretrained(model_name=self.MODEL_NAME).to(self.device)
        self.model.eval()

        print(Fore.LIGHTBLUE_EX + 'Running sanity check...')
        self.save_path = r"E:\LINGO\LingoTranscription\ASR_MODELB\temp"
        # sanity_out = self.model.transcribe([os.path.join(os.getcwd(), "DUMMY", "Client21681384326.9264379.wav")])[0][0]
        print(Fore.LIGHTCYAN_EX + "Loaded STT Lingo Live API")

    # def get_transcripts(audio_path):
    #     text =
    #     return text

    def runlocal(self, file_path):
        print("File path: ", file_path)
        result = self.model.transcribe([file_path])
        print(100 * "-")
        print("Output text: ", result)
        print(100 * "-")
        text = result[0].text if result else ""
        print("Output text: ", text)
        return result

    def runstream(self, audio_data):
        try:
            success = True
            raw_data = audio_data
            # audio = torch.from_numpy(np.frombuffer(raw_data, np.int16).flatten().astype(np.float32) / 32768.0)

            audio_clip = AudioSegment.from_raw(io.BytesIO(raw_data), sample_width=2, frame_rate=16000,
                                               channels=1)
            filename = os.path.join(self.save_path, f"Stream_{time.time()}.wav")
            audio_clip.export(filename, format="wav")
            output_text = self.model.transcribe([filename])
            print(100 * "-")
            print("Output text: ", output_text)
            print(100 * "-")
            print("Output text: ", output_text['text'])
            final_output = {"type": "LINGO", "transcription": output_text, "message": "Transcribed"}
            return final_output, success
        except Exception as e:
            final_output = {"type": "LINGO", "transcription": "", "message": "ERROR"}
            return final_output, False



if __name__ == '__main__':
    asr_infer = LingoAPIModelB()

    file_path = "/mnt/data/DUMP/pipecat_latest/pipecat_version_2/pipecat/examples/websocket/recordings_sam/merged_20250706_163651.wav"
    t1 = time.time()
    out = asr_infer.runlocal(file_path)
    t2 = time.time()
    print("Inference time: ", round((t2 - t1), 3))
