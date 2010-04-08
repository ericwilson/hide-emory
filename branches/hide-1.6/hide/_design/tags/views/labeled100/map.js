function(doc) {
    var tokens;
    if (doc.tags) {
        tokens = doc.tags.split(/\s*,\s*/i);
        tokens.map(function(token) {
if (token == 'labeled100' ) {
            emit(token, doc);
}
        });
    }
}
