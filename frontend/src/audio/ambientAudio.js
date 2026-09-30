const RECORDING_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
];

export function getPreferredRecordingMimeType() {
  if (!window.MediaRecorder?.isTypeSupported) return "";
  return RECORDING_MIME_TYPES.find((mimeType) =>
    window.MediaRecorder.isTypeSupported(mimeType)
  ) || "";
}

export async function convertRecordingToWav(recordingBlob) {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    throw new Error("Audio decoding is not supported in this browser.");
  }

  const audioContext = new AudioContextClass();
  try {
    const arrayBuffer = await recordingBlob.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    const monoSamples = mixToMono(audioBuffer);
    return new Blob([encodeWav(monoSamples, audioBuffer.sampleRate)], {
      type: "audio/wav",
    });
  } finally {
    if (audioContext.state !== "closed") {
      await audioContext.close().catch(() => {});
    }
  }
}

function mixToMono(audioBuffer) {
  const { length, numberOfChannels } = audioBuffer;
  const output = new Float32Array(length);

  for (let channel = 0; channel < numberOfChannels; channel += 1) {
    const channelData = audioBuffer.getChannelData(channel);
    for (let index = 0; index < length; index += 1) {
      output[index] += channelData[index] / numberOfChannels;
    }
  }

  return output;
}

function encodeWav(samples, sampleRate) {
  const bytesPerSample = 2;
  const blockAlign = bytesPerSample;
  const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample);
  const view = new DataView(buffer);

  writeAscii(view, 0, "RIFF");
  view.setUint32(4, 36 + samples.length * bytesPerSample, true);
  writeAscii(view, 8, "WAVE");
  writeAscii(view, 12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true);
  writeAscii(view, 36, "data");
  view.setUint32(40, samples.length * bytesPerSample, true);

  let offset = 44;
  for (let index = 0; index < samples.length; index += 1, offset += 2) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }

  return buffer;
}

function writeAscii(view, offset, text) {
  for (let index = 0; index < text.length; index += 1) {
    view.setUint8(offset + index, text.charCodeAt(index));
  }
}
