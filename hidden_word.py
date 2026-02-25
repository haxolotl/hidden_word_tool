"""
Hidden Word Finder for Cryptic Crosswords
"""

import re
import argparse
from collections import defaultdict

# ANSI color codes for terminal highlighting
RED = '\033[91m'
RESET = '\033[0m'

# Import NLTK
try:
    import nltk
    from nltk.corpus import brown, gutenberg, reuters, abc, webtext
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    print("ERROR: NLTK is required for this tool.")
    print("Install with: pip3 install nltk")
    print("Then download corpora with:")
    print("  python3 -c \"import nltk; nltk.download('brown')\"")
    print("  python3 -c \"import nltk; nltk.download('gutenberg')\"")
    print("  python3 -c \"import nltk; nltk.download('reuters')\"")
    print("  python3 -c \"import nltk; nltk.download('abc')\"")
    print("  python3 -c \"import nltk; nltk.download('webtext')\"")
    exit(1)


def load_nltk_corpus(corpus_name='all'):
    """
    Load text from NLTK corpus, filtering out punctuation tokens.
    Available corpora: 'brown', 'gutenberg', 'reuters', 'abc', 'webtext', 'all'
    """
    print(f"Loading NLTK corpus: {corpus_name}...")

    def join_words(corpus):
        # Filter tokens that contain no word characters (punctuation, symbols)
        return ' '.join(w for w in corpus.words() if re.match(r'\w', w))

    try:
        if corpus_name == 'brown':
            return join_words(brown)
        elif corpus_name == 'gutenberg':
            return join_words(gutenberg)
        elif corpus_name == 'reuters':
            return join_words(reuters)
        elif corpus_name == 'abc':
            return join_words(abc)
        elif corpus_name == 'webtext':
            return join_words(webtext)
        elif corpus_name == 'all':
            text = join_words(brown)
            text += ' ' + join_words(gutenberg)
            text += ' ' + join_words(reuters)
            try:
                text += ' ' + join_words(abc)
            except Exception:
                pass
            try:
                text += ' ' + join_words(webtext)
            except Exception:
                pass
            return text
        else:
            print(f"Unknown corpus: {corpus_name}")
            print("Available: 'brown', 'gutenberg', 'reuters', 'abc', 'webtext', 'all'")
            return None
    except LookupError:
        print(f"\nError: Corpus '{corpus_name}' not downloaded.")
        print(f"Download with: python3 -c \"import nltk; nltk.download('{corpus_name}')\"")
        return None


def find_hidden_words(target_word, corpus_text):
    """
    Find phrases in corpus that contain the target word as consecutive
    letters crossing word boundaries.

    Returns:
        List of dicts with keys:
            core_phrase     - the minimal phrase containing the hidden word
            split_pattern   - e.g. "LY | IN | G"
            target          - the search word (uppercased)
            crosses_boundaries - bool
            highlight_start - start position of hidden word within core_phrase
            highlight_end   - end position (inclusive) within core_phrase
    """
    target = target_word.upper()
    results = []
    seen_positions = set()

    sentences = re.split(r'[.!?]+', corpus_text)

    for sent_idx, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence:
            continue

        words = sentence.split()

        for span_length in range(2, min(6, len(words) + 1)):
            for start_idx in range(len(words) - span_length + 1):
                word_span = words[start_idx:start_idx + span_length]
                phrase = ' '.join(word_span)
                phrase_condensed = phrase.replace(' ', '').upper()

                if target not in phrase_condensed:
                    continue

                # Position of target in condensed phrase
                phrase_condensed_pos = phrase_condensed.find(target)

                # Map condensed positions back to original phrase positions
                char_positions = []
                for i, char in enumerate(phrase.upper()):
                    if char != ' ':
                        char_positions.append(i)

                start_orig = char_positions[phrase_condensed_pos]
                end_orig = char_positions[phrase_condensed_pos + len(target) - 1]

                # Deduplicate by absolute sentence position
                phrase_start_in_sentence = len(' '.join(words[:start_idx]))
                if start_idx > 0:
                    phrase_start_in_sentence += 1
                target_position = phrase_start_in_sentence + start_orig

                position_key = (sent_idx, target_position)
                if position_key in seen_positions:
                    continue

                boundary_info = check_boundaries(phrase, target)
                if not boundary_info['valid']:
                    continue

                seen_positions.add(position_key)

                if not boundary_info['crosses_boundaries']:
                    # Find the single word containing the target
                    core_phrase_to_use = phrase  # fallback
                    for word in phrase.split():
                        word_clean = re.sub(r'[^\w]', '', word).upper()
                        if target in word_clean:
                            core_phrase_to_use = word
                            break

                    word_upper = core_phrase_to_use.upper()
                    word_clean = re.sub(r'[^\w]', '', word_upper)
                    pos = word_clean.find(target)
                    highlight_start = pos
                    highlight_end = pos + len(target) - 1

                else:
                    core_phrase_to_use = phrase
                    highlight_start = start_orig
                    highlight_end = end_orig

                results.append({
                    'core_phrase': core_phrase_to_use,
                    'split_pattern': boundary_info['split_pattern'],
                    'target': target,
                    'crosses_boundaries': boundary_info['crosses_boundaries'],
                    'highlight_start': highlight_start,
                    'highlight_end': highlight_end,
                })

    return results


def find_reversed_hidden_words(target_word, corpus_text):
    """
    Find phrases containing the target word reversed as consecutive letters.
    e.g. "LYING" searches for "GNIYL"
    Returns same format as find_hidden_words.
    """
    reversed_word = target_word[::-1]
    results = find_hidden_words(reversed_word, corpus_text)
    for r in results:
        r['original_target'] = target_word.upper()
        r['target'] = target_word.upper()
    return results


def check_boundaries(phrase, target):
    """
    Validate hidden word placement against cryptic crossword rules.

    Rule 1: Must NOT start at word start AND end at word end (would be a trivially visible word)
    Rule 2: If fully within one word, must not touch either boundary
    """
    target = target.upper()
    phrase_upper = phrase.upper()

    phrase_condensed = phrase_upper.replace(' ', '')
    target_pos = phrase_condensed.find(target)

    if target_pos == -1:
        return {'valid': False}

    char_positions = []
    for i, char in enumerate(phrase_upper):
        if char != ' ':
            char_positions.append(i)

    start_orig = char_positions[target_pos]
    end_orig = char_positions[target_pos + len(target) - 1]

    starts_at_word_start = (start_orig == 0) or (phrase_upper[start_orig - 1] == ' ')
    ends_at_word_end = (end_orig == len(phrase_upper) - 1) or (phrase_upper[end_orig + 1] == ' ')

    split_pattern = find_split_pattern(phrase, target, start_orig, end_orig)
    crosses_boundaries = '|' in split_pattern

    if starts_at_word_start and ends_at_word_end:
        return {'valid': False}

    if not crosses_boundaries and (starts_at_word_start or ends_at_word_end):
        return {'valid': False}

    return {
        'valid': True,
        'crosses_boundaries': crosses_boundaries,
        'split_pattern': split_pattern,
        'starts_at_word_start': starts_at_word_start,
        'ends_at_word_end': ends_at_word_end,
    }


def find_split_pattern(phrase, target, start_pos, end_pos):
    """
    Returns a pattern like "LY | IN | G" showing how the target is
    split across word boundaries in the phrase.
    """
    phrase_upper = phrase.upper()
    pattern_parts = []
    current_part = ""

    for i in range(start_pos, end_pos + 1):
        char = phrase_upper[i]
        if char == ' ':
            if current_part:
                pattern_parts.append(current_part)
                current_part = ""
        else:
            current_part += char

    if current_part:
        pattern_parts.append(current_part)

    return ' | '.join(pattern_parts)


def highlight_hidden_word(phrase, target, start, end, mode='html'):
    """
    Highlight the hidden word within a phrase.
    mode='html'     - wraps hidden letters in <span class="highlight"> tags (default)
    mode='terminal' - wraps hidden letters in ANSI colour codes for terminal output
    """
    if mode == 'terminal':
        return phrase[:start] + RED + phrase[start:end + 1] + RESET + phrase[end + 1:]
    return (phrase[:start] +
            '<span class="highlight">' +
            phrase[start:end + 1] +
            '</span>' +
            phrase[end + 1:])


def format_results_for_display(results, target_word):
    """
    Group results by split pattern, count unique phrases, sort by frequency.
    Returns a list of (pattern, [(phrase, count), ...]) tuples.
    Used by both CLI and Flask server.
    """
    by_pattern = defaultdict(lambda: defaultdict(int))
    for result in results:
        by_pattern[result['split_pattern']][result['core_phrase']] += 1

    sorted_patterns = sorted(by_pattern.items(),
                             key=lambda x: sum(x[1].values()),
                             reverse=True)

    formatted = []
    for pattern, phrases in sorted_patterns:
        sorted_phrases = sorted(phrases.items(), key=lambda x: x[1], reverse=True)
        formatted.append((pattern, sorted_phrases))

    return formatted


def search_and_display(target_word, nltk_corpus='all'):
    """CLI entry point: search and print results to terminal."""
    corpus_text = load_nltk_corpus(nltk_corpus)
    if corpus_text is None:
        return []

    print(f"\n{'='*70}")
    print(f"Searching for hidden word: {target_word.upper()}")
    print(f"Source: NLTK {nltk_corpus} corpus")
    print(f"Corpus size: {len(corpus_text):,} characters")
    print(f"{'='*70}\n")

    results = find_hidden_words(target_word, corpus_text)

    if not results:
        print("No results found!")
        return []

    print(f"Found {len(results)} total occurrences:\n")

    # Build lookup for highlight positions
    position_lookup = {r['core_phrase']: (r['highlight_start'], r['highlight_end'])
                       for r in results}

    formatted = format_results_for_display(results, target_word)

    for pattern, phrases in formatted:
        total = sum(c for _, c in phrases)
        print(f"\n  Pattern: {pattern} ({len(phrases)} unique phrases, {total} total)")
        print(f"  {'-'*60}")
        for phrase, count in phrases:
            start, end = position_lookup.get(phrase, (0, len(phrase) - 1))
            highlighted = highlight_hidden_word(phrase, target_word, start, end, mode='terminal')
            suffix = f" ({count})" if count > 1 else ""
            print(f"    • {highlighted}{suffix}")

    print(f"\n{'='*70}\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Find hidden words in NLTK corpora for cryptic crossword clues'
    )
    parser.add_argument('word', type=str, help='The word to hide (e.g., LYING)')
    parser.add_argument('--corpus', type=str, default='all',
                        choices=['brown', 'gutenberg', 'reuters', 'abc', 'webtext', 'all'],
                        help='Which NLTK corpus to use (default: all)')
    args = parser.parse_args()

    print("="*70)
    print("HIDDEN WORD FINDER FOR CRYPTIC CROSSWORDS")
    print("="*70)

    results = search_and_display(args.word, nltk_corpus=args.corpus)

    if results:
        print("\n" + "="*70)
        print("PATTERN ANALYSIS")
        print("="*70)
        patterns = defaultdict(int)
        for r in results:
            patterns[r['split_pattern']] += 1
        print(f"\nSplit patterns found for '{args.word.upper()}':")
        for pattern, count in sorted(patterns.items(), key=lambda x: -x[1]):
            print(f"  {pattern}: {count} occurrences")
        print("\n→ These patterns can be used for targeted wordlist searching!")
        print("="*70)