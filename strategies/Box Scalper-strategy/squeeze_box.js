/**
 * Squeeze Box - stateless JS implementation
 * Converted 1:1 from Pine logic; computes series across provided klineData (oldest->newest)
 * klineData elements: {open, high, low, close, volume}
 */

function _smaAt(arr, period, idx) {
    if (idx + 1 < period) return null;
    let sum = 0;
    for (let i = idx - period + 1; i <= idx; i++) sum += arr[i];
    return sum / period;
}

function _emaAt(arr, period, idx) {
    if (idx + 1 < period) return null;
    const k = 2 / (period + 1);
    let sum = 0;
    for (let i = 0; i < period; i++) sum += arr[i];
    let ema = sum / period;
    for (let i = period; i <= idx; i++) {
        ema = (arr[i] - ema) * k + ema;
    }
    return ema;
}

function _wmaAt(arr, period, idx) {
    if (idx + 1 < period) return null;
    let weightedSum = 0;
    let sumW = 0;
    for (let i = 0; i < period; i++) {
        const w = period - i;
        weightedSum += arr[idx - period + 1 + i] * w;
        sumW += w;
    }
    return weightedSum / sumW;
}

function _stdevAt(arr, period, idx) {
    if (idx + 1 < period) return null;
    let sum = 0;
    for (let i = idx - period + 1; i <= idx; i++) sum += arr[i];
    const mean = sum / period;
    let variance = 0;
    for (let i = idx - period + 1; i <= idx; i++) variance += Math.pow(arr[i] - mean, 2);
    variance = variance / period;
    return Math.sqrt(variance);
}

function _highestAt(arr, period, idx) {
    if (idx + 1 < period) return null;
    let hi = -Infinity;
    for (let i = idx - period + 1; i <= idx; i++) if (arr[i] > hi) hi = arr[i];
    return hi;
}

function _lowestAt(arr, period, idx) {
    if (idx + 1 < period) return null;
    let lo = Infinity;
    for (let i = idx - period + 1; i <= idx; i++) if (arr[i] < lo) lo = arr[i];
    return lo;
}

function _hullAt(arr, period, idx) {
    if (idx + 1 < period) return null;
    const halfPer = Math.max(1, Math.floor(period / 2));
    const sqrtPerR = Math.max(1, Math.round(Math.sqrt(period)));
    const adjusted = [];
    for (let j = Math.max(period - 1, halfPer - 1); j <= idx; j++) {
        const w_half = _wmaAt(arr, halfPer, j);
        const w_full = _wmaAt(arr, period, j);
        if (w_half === null || w_full === null) continue;
        adjusted.push(2 * w_half - w_full);
    }
    if (adjusted.length < sqrtPerR) return null;
    const last = adjusted.slice(-sqrtPerR);
    let weightedSum = 0;
    let sumW = 0;
    for (let i = 0; i < last.length; i++) {
        const w = last.length - i;
        weightedSum += last[i] * w;
        sumW += w;
    }
    return weightedSum / sumW;
}

function calculateLatestSqueezeBox(klineData, params = {}) {
    const per = params.period || 21;
    const matype = params.maType || 'EMA';
    const ndev = params.nDev !== undefined ? params.nDev : 2;
    const sr = params.srThreshold !== undefined ? params.srThreshold : 50;

    const n = klineData.length;
    if (n === 0) return null;

    const src = new Array(n);
    const closes = new Array(n);
    for (let i = 0; i < n; i++) {
        const k = klineData[i];
        closes[i] = k.close;
        src[i] = (k.high + k.low + k.close) / 3.0;
    }

    const maSeries = new Array(n).fill(null);
    const buSeries = new Array(n).fill(null);
    const bdSeries = new Array(n).fill(null);
    const bwSeries = new Array(n).fill(null);
    const sqpSeries = new Array(n).fill(null);
    const sqzSeries = new Array(n).fill(0);
    const boxhSeries = new Array(n).fill(null);
    const boxlSeries = new Array(n).fill(null);

    for (let i = 0; i < n; i++) {
        let ma = null;
        if (matype === 'EMA') ma = _emaAt(closes, per, i);
        else if (matype === 'SMA') ma = _smaAt(closes, per, i);
        else if (matype === 'HULLMA') ma = _hullAt(closes, per, i);
        if (ma === null) ma = _emaAt(closes, per, i);
        maSeries[i] = ma;

        const stdev = _stdevAt(closes, per, i);
        if (ma === null || stdev === null) continue;
        const dev = stdev * ndev;
        const bu = ma + dev;
        const bd = ma - dev;
        buSeries[i] = bu;
        bdSeries[i] = bd;
        bwSeries[i] = bu - bd;

        const buh = _highestAt(buSeries, per, i);
        const bdl = _lowestAt(bdSeries, per, i);
        const brng = (buh !== null && bdl !== null) ? (buh - bdl) : 0;
        const sqp = (brng !== 0) ? (100.0 * (bu - bd) / brng) : 0;
        sqpSeries[i] = sqp;
        sqzSeries[i] = (sqp < sr) ? 1 : 0;

        const srcHi = (i >= per - 1) ? _highestAt(src, per, i) : src[i];
        const srcLo = (i >= per - 1) ? _lowestAt(src, per, i) : src[i];
        boxhSeries[i] = sqzSeries[i] ? srcHi : src[i];
        boxlSeries[i] = sqzSeries[i] ? srcLo : src[i];
    }

    const trueIdx = [];
    for (let i = 0; i < n; i++) if (sqzSeries[i]) trueIdx.push(i);

    const lastIndex = n - 1;
    let bh = null;
    let bl = null;
    const occ = trueIdx.filter(idx => idx <= lastIndex);
    if (occ.length >= 2) {
        const prevIdx = occ[occ.length - 2];
        bh = boxhSeries[prevIdx];
        bl = boxlSeries[prevIdx];
    } else if (occ.length === 1) {
        bh = boxhSeries[lastIndex] !== null ? boxhSeries[lastIndex] : null;
        bl = boxlSeries[lastIndex] !== null ? boxlSeries[lastIndex] : null;
    } else {
        bh = boxhSeries[lastIndex] !== null ? boxhSeries[lastIndex] : null;
        bl = boxlSeries[lastIndex] !== null ? boxlSeries[lastIndex] : null;
    }

    const ma = maSeries[lastIndex];
    const bu = buSeries[lastIndex];
    const bd = bdSeries[lastIndex];
    const dev = (bu !== null && bd !== null) ? (bu - bd) / 2 : null;
    const sqp = sqpSeries[lastIndex] !== null ? sqpSeries[lastIndex] : null;
    const sqz = sqzSeries[lastIndex];

    return {
        basis: ma,
        bh: bh,
        bl: bl,
        sqz: sqz,
        sqp: sqp,
        bu: bu,
        bd: bd,
        ma: ma,
        dev: dev,
    };
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = { calculateLatestSqueezeBox };
}
