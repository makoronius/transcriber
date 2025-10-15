"""
SRT Cleanup Tool
-----------------
Cleans up hallucinated/garbage text from SRT subtitle files.

Features:
- Remove repeated patterns and filler text
- Remove segments with excessive repetition
- Configurable filter patterns
- Detect and analyze trashy inclusions
- Batch processing
"""

import re
import os
import sys
import argparse
import copy
from pathlib import Path
from collections import Counter
import yaml


DEFAULT_FILTERS = {
    'bad_phrases': [
        "hvala što pratite kanal",
        "Hvala vam",
        "subscribe",
        "captioned by",
        "prodavanje",
        "teksting av",
        "thanks for watching",
        "teksting av nicolai winther",
        "like and subscribe",
        "don't forget to subscribe",
        "Privećajuće",  # Common hallucination
        "Apoće",  # Common hallucination
    ],
    'repeated_patterns': [
        r'(\b\w+\b)(?:,?\s*\1){5,}',  # Word repeated 5+ times
        r'(\b\w{1,3}\b)(?:,?\s*\1){10,}',  # Short word repeated 10+ times
        r'^(\w+)\s+\1\s+\1',  # Triple word repetition at start
    ],
    'garbage_patterns': [
        r'^[\s,\.]+$',  # Only whitespace/punctuation
        r'^[a-zA-Z]{1}[,\s]+$',  # Single letter with punctuation
        r'(.)\1{20,}',  # Character repeated 20+ times
        r'^([А-я]{1,3},?\s*){10,}$',  # Short Cyrillic words repeated
    ],
    'min_segment_duration': 0.3,  # Seconds
    'max_repetition_ratio': 0.7,  # 70% repetition is suspicious
}


class SRTSegment:
    """Represents a single SRT subtitle segment"""

    def __init__(self, index, start_time, end_time, text):
        self.index = index
        self.start_time = start_time
        self.end_time = end_time
        self.text = text.strip()

    @property
    def duration(self):
        """Calculate duration in seconds"""
        return self.time_to_seconds(self.end_time) - self.time_to_seconds(self.start_time)

    @staticmethod
    def time_to_seconds(time_str):
        """Convert SRT time format to seconds"""
        hours, minutes, rest = time_str.split(':')
        seconds, milliseconds = rest.replace(',', '.').split('.')
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(milliseconds) / 1000

    @staticmethod
    def seconds_to_time(seconds):
        """Convert seconds to SRT time format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def __str__(self):
        return f"{self.index}\n{self.start_time} --> {self.end_time}\n{self.text}\n"


def load_srt(file_path):
    """Load SRT file into segments"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    segments = []
    blocks = re.split(r'\n\s*\n', content.strip())

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                index = int(lines[0])
                times = lines[1]
                text = '\n'.join(lines[2:])

                if '-->' in times:
                    start, end = times.split('-->')
                    segment = SRTSegment(index, start.strip(), end.strip(), text)
                    segments.append(segment)
            except (ValueError, IndexError):
                continue

    return segments


def save_srt(segments, file_path):
    """Save segments to SRT file"""
    with open(file_path, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(segments, 1):
            seg.index = i  # Reindex
            f.write(str(seg) + '\n')


def analyze_repetition(text):
    """Analyze text for repetition ratio"""
    words = text.lower().split()
    if not words:
        return 0.0

    # Count word frequencies
    word_counts = Counter(words)
    most_common = word_counts.most_common(1)[0][1] if word_counts else 0

    return most_common / len(words)


def shorten_repeated_patterns(text):
    """Shorten repeated patterns in text instead of removing completely"""
    modified = False
    original_text = text

    # Pattern 1: Word repeated 5+ times (e.g., "je, je, je, je, je" -> "je, je")
    pattern1 = r'(\b\w+\b)((?:,?\s*\1){4,})'
    def replace_word_rep(match):
        word = match.group(1)
        # Keep 1-2 instances instead of all
        return f"{word}, {word} [repeated]"

    text = re.sub(pattern1, replace_word_rep, text, flags=re.IGNORECASE)
    if text != original_text:
        modified = True
        original_text = text

    # Pattern 2: Short syllables repeated excessively (e.g., "Privećajuće" repeated)
    pattern2 = r'(\b\w{3,15}\b)((?:\s+\1){3,})'
    def replace_phrase_rep(match):
        phrase = match.group(1)
        return f"{phrase} {phrase} [repeated]"

    text = re.sub(pattern2, replace_phrase_rep, text, flags=re.IGNORECASE)
    if text != original_text:
        modified = True

    # Pattern 3: Single character repeated many times (e.g., "aaaaaaaa" -> "aa")
    pattern3 = r'(\w)\1{10,}'
    def replace_char_rep(match):
        char = match.group(1)
        return f"{char}{char} [repeated]"

    text = re.sub(pattern3, replace_char_rep, text)
    if text != original_text:
        modified = True

    return text, modified


def clean_segment_text(segment, filters):
    """Clean segment text by shortening repeated patterns"""
    text = segment.text

    # First, try to shorten repeated patterns
    cleaned_text, was_modified = shorten_repeated_patterns(text)

    if was_modified:
        segment.text = cleaned_text
        return segment, 'shortened', 'Repeated pattern shortened'

    # Check for completely bad content that should be removed
    text_lower = text.lower()

    # Check duration
    if segment.duration < filters.get('min_segment_duration', 0.3):
        return None, 'removed', "Too short duration"

    # Check bad phrases (these are removed completely)
    for phrase in filters.get('bad_phrases', []):
        if phrase.lower() in text_lower:
            return None, 'removed', f"Contains bad phrase: {phrase}"

    # Check garbage patterns (these are removed completely)
    for pattern in filters.get('garbage_patterns', []):
        if re.search(pattern, text, re.IGNORECASE):
            return None, 'removed', f"Matches garbage pattern: {pattern}"

    # Check for very short meaningless text
    if len(text.split()) <= 1 and len(text) < 8:
        return None, 'removed', "Too short text"

    # If nothing triggered, keep as is
    return segment, 'kept', None


def is_hallucination(segment, filters):
    """Check if segment contains hallucinated/garbage text (for analysis)"""
    text = segment.text
    text_lower = text.lower()

    # Check duration
    if segment.duration < filters.get('min_segment_duration', 0.3):
        return True, "Too short"

    # Check bad phrases
    for phrase in filters.get('bad_phrases', []):
        if phrase.lower() in text_lower:
            return True, f"Contains bad phrase: {phrase}"

    # Check repeated patterns (for detection, not removal)
    for pattern in filters.get('repeated_patterns', []):
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"Matches repeated pattern: {pattern}"

    # Check garbage patterns
    for pattern in filters.get('garbage_patterns', []):
        if re.search(pattern, text, re.IGNORECASE):
            return True, f"Matches garbage pattern: {pattern}"

    # Check repetition ratio
    repetition = analyze_repetition(text)
    max_ratio = filters.get('max_repetition_ratio', 0.7)
    if repetition > max_ratio:
        return True, f"High repetition ratio: {repetition:.2%}"

    # Check for very short text
    if len(text.split()) <= 1 and len(text) < 8:
        return True, "Too short text"

    return False, None


def analyze_srt(file_path, filters=None):
    """Analyze SRT file for issues"""
    if filters is None:
        filters = DEFAULT_FILTERS

    segments = load_srt(file_path)
    issues = []

    for seg in segments:
        is_bad, reason = is_hallucination(seg, filters)
        if is_bad:
            issues.append({
                'index': seg.index,
                'text': seg.text,
                'reason': reason,
                'duration': seg.duration
            })

    return segments, issues


def cleanup_srt(input_path, output_path=None, filters=None, dry_run=False):
    """Clean up SRT file"""
    if filters is None:
        filters = DEFAULT_FILTERS

    if output_path is None:
        output_path = input_path.replace('.srt', '_clean.srt')

    segments, issues = analyze_srt(input_path, filters)

    print(f"📄 Analyzing: {os.path.basename(input_path)}")
    print(f"   Total segments: {len(segments)}")
    print(f"   Issues found: {len(issues)}")

    if issues:
        print("\n🔍 Issues detected:")
        for issue in issues[:10]:  # Show first 10
            print(f"   [{issue['index']}] {issue['reason']}")
            print(f"       Text: {issue['text'][:60]}...")

        if len(issues) > 10:
            print(f"   ... and {len(issues) - 10} more")

    # Process segments: shorten repeated patterns or remove completely
    clean_segments = []
    removed = 0
    shortened = 0

    for seg in segments:
        # Make a copy to avoid modifying original
        seg_copy = copy.deepcopy(seg)

        result_seg, action, reason = clean_segment_text(seg_copy, filters)

        if action == 'kept':
            clean_segments.append(seg_copy)
        elif action == 'shortened':
            clean_segments.append(result_seg)
            shortened += 1
        elif action == 'removed':
            removed += 1

    print(f"\n✅ Cleaned:")
    print(f"   {shortened} segments had repeated patterns shortened")
    print(f"   {removed} segments removed completely")
    print(f"   {len(clean_segments)} segments remaining")

    if not dry_run:
        save_srt(clean_segments, output_path)
        print(f"💾 Saved to: {output_path}")
    else:
        print("🔍 Dry run mode - no files written")

    return clean_segments, issues


def load_custom_filters(config_path='config.yaml'):
    """Load custom filters from config file"""
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('hallucination_filters', DEFAULT_FILTERS)
        except Exception as e:
            print(f"⚠️  Warning: Failed to load custom filters: {e}")

    return DEFAULT_FILTERS


def batch_cleanup(directory, filters=None, dry_run=False):
    """Clean up all SRT files in a directory"""
    if filters is None:
        filters = load_custom_filters()

    srt_files = list(Path(directory).rglob('*.srt'))

    # Skip already cleaned files
    srt_files = [f for f in srt_files if '_clean' not in f.name]

    print(f"🔍 Found {len(srt_files)} SRT files")
    print("=" * 60)

    total_removed = 0

    for srt_file in srt_files:
        try:
            _, issues = cleanup_srt(str(srt_file), filters=filters, dry_run=dry_run)
            total_removed += len(issues)
            print()
        except Exception as e:
            print(f"❌ Error processing {srt_file.name}: {e}")
            print()

    print("=" * 60)
    print(f"✅ Total segments removed: {total_removed}")


def main():
    parser = argparse.ArgumentParser(description='Clean up SRT subtitle files')
    parser.add_argument('input', help='Input SRT file or directory')
    parser.add_argument('--output', '-o', help='Output file (default: input_clean.srt)')
    parser.add_argument('--dry-run', action='store_true', help='Analyze without writing')
    parser.add_argument('--batch', action='store_true', help='Process all SRT files in directory')
    parser.add_argument('--config', default='config.yaml', help='Config file with custom filters')

    args = parser.parse_args()

    # Load filters
    filters = load_custom_filters(args.config)

    if args.batch:
        if not os.path.isdir(args.input):
            print("❌ Error: --batch requires a directory")
            sys.exit(1)
        batch_cleanup(args.input, filters=filters, dry_run=args.dry_run)
    else:
        if not os.path.isfile(args.input):
            print(f"❌ Error: File not found: {args.input}")
            sys.exit(1)
        cleanup_srt(args.input, args.output, filters=filters, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
