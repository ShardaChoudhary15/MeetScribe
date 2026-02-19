from flask import Flask, request, jsonify
import requests
import logging

# ── Logging (all steps printed to your terminal) ─────────────────────────────
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

app = Flask(__name__)

ASSEMBLYAI_API_KEY = '4b4c7c5b750a4a828a230300ca4e0836'
BASE_HEADERS = {'authorization': ASSEMBLYAI_API_KEY}

# ── CORS ──────────────────────────────────────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'POST, GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/assembly-api', methods=['GET', 'POST', 'OPTIONS'])
def assembly_api():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    action = request.args.get('action') or request.form.get('action') or ''
    log.info(f"action={action!r}")

    # ── UPLOAD ────────────────────────────────────────────────────────────────
    if action == 'upload':
        if 'audio' not in request.files:
            log.error("No audio file in request")
            return jsonify({'success': False, 'error': 'No audio file provided'})

        audio_data = request.files['audio'].read()
        log.info(f"Uploading {len(audio_data)} bytes to AssemblyAI...")

        resp = requests.post(
            'https://api.assemblyai.com/v2/upload',
            headers={**BASE_HEADERS, 'Content-Type': 'application/octet-stream'},
            data=audio_data
        )
        log.info(f"Upload → HTTP {resp.status_code}: {resp.text[:300]}")

        if resp.status_code == 200:
            upload_url = resp.json().get('upload_url')
            return jsonify({'success': True, 'data': {'upload_url': upload_url}})
        return jsonify({'success': False, 'error': f'Upload failed [{resp.status_code}]: {resp.text}'})

    # ── TRANSCRIBE ────────────────────────────────────────────────────────────
    if action == 'transcribe':
        audio_url = request.form.get('audio_url', '')
        log.info(f"Transcribe for audio_url={audio_url!r}")

        if not audio_url:
            return jsonify({'success': False, 'error': 'No audio URL provided'})

        payload = {
            'audio_url': audio_url,
            'summarization': True,
            'summary_model': 'informative',
            'summary_type': 'bullets'
        }

        resp = requests.post(
            'https://api.assemblyai.com/v2/transcript',
            headers={**BASE_HEADERS, 'Content-Type': 'application/json'},
            json=payload
        )
        log.info(f"Transcribe → HTTP {resp.status_code}: {resp.text[:300]}")

        if resp.status_code == 200:
            transcript_id = resp.json().get('id')
            log.info(f"Got transcript_id={transcript_id}")
            return jsonify({'success': True, 'data': {'transcript_id': transcript_id}})
        return jsonify({'success': False, 'error': f'Transcription failed [{resp.status_code}]: {resp.text}'})

    # ── STATUS ────────────────────────────────────────────────────────────────
    if action == 'status':
        transcript_id = request.args.get('transcript_id', '')
        log.info(f"Status check for transcript_id={transcript_id!r}")

        if not transcript_id:
            return jsonify({'success': False, 'error': 'No transcript ID provided'})

        resp = requests.get(
            f'https://api.assemblyai.com/v2/transcript/{transcript_id}',
            headers=BASE_HEADERS
        )
        log.info(f"Status → HTTP {resp.status_code}: {resp.text[:500]}")

        if resp.status_code == 200:
            result  = resp.json()
            status  = result.get('status')
            text    = result.get('text')
            summary = result.get('summary')
            error   = result.get('error')   # AssemblyAI error field
            log.info(f"status={status} | has_text={bool(text)} | has_summary={bool(summary)} | aai_error={error!r}")

            if status == 'error':
                return jsonify({'success': False, 'error': f'AssemblyAI error: {error}'})

            return jsonify({'success': True, 'data': {'status': status, 'text': text, 'summary': summary}})
        return jsonify({'success': False, 'error': f'Status check failed [{resp.status_code}]: {resp.text}'})

    # ── TEST (open in browser to verify API key) ──────────────────────────────
    if action == 'test':
        resp = requests.get('https://api.assemblyai.com/v2/transcript',
                            headers=BASE_HEADERS, params={'limit': 1})
        if resp.status_code == 200:
            return jsonify({'success': True, 'message': 'API key is valid!'})
        return jsonify({'success': False, 'message': 'API key invalid or unreachable',
                        'http_status': resp.status_code, 'body': resp.text})

    return jsonify({'success': False, 'error': f'Invalid action: {action!r}'})


if __name__ == '__main__':
    print("\n" + "="*58)
    print("  Flask backend running  →  http://localhost:5000")
    print("  Verify API key        →  http://localhost:5000/assembly-api?action=test")
    print("="*58 + "\n")
    app.run(debug=True, port=5000)
