-- This file contains the search_phrase query, to find the appearances of phrases inside of document sentences.

SELECT document_id, sentence, sentence_index AS start_index, sentence_index + words_count - 1 AS end_index
FROM phrase NATURAL JOIN word_in_phrase NATURAL JOIN
    (SELECT phrase_id, document_id, sentence, sentence_index, word_id,
        sentence_index - ROW_NUMBER() OVER (PARTITION BY sentence ORDER BY sentence_index) AS consecutive_phrase_words
    FROM word_appearance NATURAL JOIN word_in_phrase
    WHERE phrase_id == ?
	GROUP BY document_id, sentence, sentence_index)
GROUP BY document_id, sentence, consecutive_phrase_words, phrase_index - sentence_index
HAVING COUNT(sentence_index) == words_count
ORDER BY document_id, sentence, sentence_index