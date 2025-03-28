lint:
    ruff check . --fix

commit message:
    git add .
    git commit -m "{{message}}"
    git push
