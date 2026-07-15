# Instructions for setp:
- Step 0: pull this repository using `git clone https://github.com/PacificBird/polytalk.git`.
- Step 1: Install docker compose. If you're on Linux, you probably already know how to do this intuitive. If you're on a differenet platform or don't know how, go here: https://docs.docker.com/compose/install/, or look up "how to set up docker compose".
- Step 2: Build and run the containers by doing `docker compose build`, followed by `docker compose up`.
- Step 3: Download the LLM for translation. Inside the `ollama` container, run `ollama pull translategemma:4b`. If you're in the command line on Linux this can be done by doing `docker exec -it ollama ollama pull translategemma:4b`.

# How to use
Go to `localhost:9000` in your web browser, hit the config button to select your audio input, and make sure the following script is in the "custom prompt" box:  
  
"You are a professional English (EN) and Spanish (ES) interpreter in a meeting. Your goal is to accurately convey the meaning and nuances of the original English and Spanish text, and translate one into the other."

Then hit the button in the middle shaped like a text box (the conversation button) and that's it! Fair warning, this is set to run on the CPU so that it's plug and play for anyone, but this makes it pretty damn slow. This should not be relied upon, but used as a secondary aid. I will work on making a branch that uses GPU acceleration for those that have it.
