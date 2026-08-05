export function computePeaks(data, count) {
  const block = Math.floor(data.length / count)
  const peaks = new Array(count)
  for (let i = 0; i < count; i++) {
    let max = 0
    for (let j = 0; j < block; j++) {
      const v = Math.abs(data[i * block + j])
      if (v > max) max = v
    }
    peaks[i] = max
  }
  return peaks
}

if (typeof self !== 'undefined' && typeof self.document === 'undefined') {
  self.onmessage = (e) => {
    const { data, count } = e.data
    self.postMessage({ peaks: computePeaks(data, count) })
  }
}
