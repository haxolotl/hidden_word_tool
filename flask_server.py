from flask import Flask, request, render_template
from collections import defaultdict
from hidden_word import find_hidden_words, highlight_hidden_word

app = Flask(__name__)

# Load corpus at startup
CORPUS_DATA = {}
SEARCH_CACHE = {}

def get_corpus_data():
    """Load corpus data once at startup as joined text strings"""
    if not CORPUS_DATA:
        import nltk
        for name, corpus in [('brown', nltk.corpus.brown),
                             ('gutenberg', nltk.corpus.gutenberg),
                             ('reuters', nltk.corpus.reuters),
                             ('abc', nltk.corpus.abc),
                             ('webtext', nltk.corpus.webtext)]:
            CORPUS_DATA[name] = ' '.join(corpus.words())
            print(f"  Loaded '{name}' ({len(CORPUS_DATA[name]):,} characters)")
        CORPUS_DATA['all'] = ' '.join(
            CORPUS_DATA[name] for name in ['brown', 'gutenberg', 'reuters', 'abc', 'webtext']
        )
        print(f"  Combined 'all' ({len(CORPUS_DATA['all']):,} characters)")
    return CORPUS_DATA

get_corpus_data()  # Load at startup

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/hidden')
def hidden():
    """Returns loading page immediately"""
    word = request.args.get('word', '').strip().upper()
    
    if not word:
        return render_template('results.html', error="No word provided")
    
    corpus = request.args.get('corpus', 'all')
    return render_template('loading.html', word=word, corpus=corpus)

def perform_search(search_word, display_label, cache_key, corpus):
    """Shared search logic for hidden and reversed hidden routes."""
    if cache_key in SEARCH_CACHE:
        return render_template('results.html', **SEARCH_CACHE[cache_key])

    try:
        corpus_text = CORPUS_DATA.get(corpus)
        if corpus_text is None:
            return render_template('results.html', error=f"Unknown corpus: {corpus}")

        results = find_hidden_words(search_word, corpus_text)

        if not results:
            template_data = {'word': display_label, 'results': [], 'total': 0}
            SEARCH_CACHE[cache_key] = template_data
            return render_template('results.html', **template_data)

        pattern_groups = defaultdict(lambda: defaultdict(int))
        total_count = 0

        for result in results:
            phrase = result['core_phrase']
            pattern = result['split_pattern']
            highlighted = highlight_hidden_word(
                phrase, search_word,
                result['highlight_start'],
                result['highlight_end']
            )
            pattern_groups[pattern][highlighted] += 1
            total_count += 1

        sorted_patterns = sorted(pattern_groups.items(),
                                 key=lambda x: sum(x[1].values()),
                                 reverse=True)

        formatted_results = []
        for pattern, phrases in sorted_patterns:
            sorted_phrases = sorted(phrases.items(), key=lambda x: x[1], reverse=True)
            formatted_results.append((pattern, sorted_phrases))

        template_data = {
            'word': display_label,
            'results': formatted_results,
            'total': total_count
        }

        SEARCH_CACHE[cache_key] = template_data
        return render_template('results.html', **template_data)

    except Exception as e:
        return render_template('results.html', error=f"Search error: {str(e)}")


@app.route('/hidden/search')
def hidden_search():
    word = request.args.get('word', '').strip().upper()
    corpus = request.args.get('corpus', 'all')
    return perform_search(word, word, f"hidden:{word}:{corpus}", corpus)


@app.route('/reversed-hidden')
def reversed_hidden():
    """Returns loading page for reversed hidden search"""
    word = request.args.get('word', '').strip().upper()

    if not word:
        return render_template('results.html', error="No word provided")

    corpus = request.args.get('corpus', 'all')
    return render_template('loading.html', word=word, corpus=corpus)


@app.route('/reversed-hidden/search')
def reversed_hidden_search():
    word = request.args.get('word', '').strip().upper()
    corpus = request.args.get('corpus', 'all')
    reversed_word = word[::-1]
    label = f"{word} (Reversed Hidden: {reversed_word})"
    return perform_search(reversed_word, label, f"rev_hidden:{word}:{corpus}", corpus)

if __name__ == '__main__':
    print("Starting Hidden Word Finder server...")
    print("Server running at http://localhost:5000")
    app.run(debug=True, port=5000)