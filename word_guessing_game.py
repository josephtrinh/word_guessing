import random
import string
import requests
import sys

def call_api(guess_word, seed):
    """
    Call the API to check the guess word.
    
    Args:
        guess_word (str): The word to guess
        seed (int, optional): Random seed for the API. Defaults to None.
    
    Returns:
        list: API response with results for each letter
    """
    # if seed is None:
    #     seed = random.randint(1, 10000)
    
    url = "https://wordle.votee.dev:8000/random"
    params = {
        "guess": guess_word,
        "size": len(guess_word),
        "seed": seed
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling API: {e}")
        return None

def generate_initial_word():
    """
    Generate a random word with a random length between 1 and 15 letters.
    
    Returns:
        str: A random word
    """
    length = random.randint(1, 15)
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))

def analyze_response(response, word_length, absent_letters, present_letters, correct_letters, letter_constraints):
    """
    Analyze the API response and update tracking dictionaries.
    
    Args:
        response (list): API response with results for each letter
        word_length (int): Length of the guessed word
        absent_letters (set): Set of letters known to be absent
        present_letters (dict): Dictionary of letters known to be present
        correct_letters (dict): Dictionary of letters known to be in correct positions
        letter_constraints (dict): Dictionary of minimum letter counts
    
    Returns:
        float: Correct percentage
    """
    for item in response:
        slot = item["slot"]
        letter = item["guess"]
        result = item["result"]
        
        if result == "absent":
            # Only mark as absent if it's not already marked as present or correct
            if letter not in present_letters and not any(correct_letters.get(pos) == letter for pos in range(word_length)):
                absent_letters.add(letter)
        elif result == "present":
            if letter not in present_letters:
                present_letters[letter] = []
            if slot not in present_letters[letter]:
                present_letters[letter].append(slot)
            
            # Update minimum count for this letter
            letter_count = sum(1 for item in response if item["guess"] == letter and 
                              (item["result"] == "present" or item["result"] == "correct"))
            letter_constraints[letter] = max(letter_constraints.get(letter, 0), letter_count)
        elif result == "correct":
            correct_letters[slot] = letter
            
            # Update minimum count for this letter
            letter_count = sum(1 for item in response if item["guess"] == letter and 
                              (item["result"] == "present" or item["result"] == "correct"))
            letter_constraints[letter] = max(letter_constraints.get(letter, 0), letter_count)
    
    # Calculate correct percentage
    correct_percentage = (len(correct_letters) / word_length) * 100
    
    return correct_percentage

def generate_next_word(word_length, absent_letters, present_letters, correct_letters, letter_constraints, previous_guesses):
    """
    Generate the next word to guess based on current constraints.
    
    Args:
        word_length (int): Length of the word to guess
        absent_letters (set): Letters that are not in the word
        present_letters (dict): Letters that are in the word but in wrong positions
        correct_letters (dict): Letters that are in the correct positions
        letter_constraints (dict): Minimum count for each letter
        previous_guesses (list): List of previously guessed words
    
    Returns:
        str: The next word to guess
    """
    while True:
        new_word = [''] * word_length
        
        # Fill in correct letters
        for position, letter in correct_letters.items():
            new_word[position] = letter
        
        # Fill in remaining positions
        available_letters = [l for l in string.ascii_lowercase if l not in absent_letters]
        
        # Make sure we include present letters
        for letter, positions in present_letters.items():
            # Ensure we don't put present letters in positions where they were already tried
            available_positions = [i for i in range(word_length) if i not in positions and i not in correct_letters]
            
            if available_positions:
                # Determine how many of this letter we need to include
                min_count = letter_constraints.get(letter, 1)
                current_count = new_word.count(letter)
                
                # Add more of this letter if needed
                for _ in range(max(0, min_count - current_count)):
                    if available_positions:
                        pos = random.choice(available_positions)
                        new_word[pos] = letter
                        available_positions.remove(pos)
        
        # Fill remaining empty positions with random letters
        for i in range(word_length):
            if new_word[i] == '':
                new_word[i] = random.choice(available_letters)
        
        generated_word = ''.join(new_word)
        
        # Check if this word has been guessed before
        if generated_word not in previous_guesses:
            return generated_word

def play_guessing_game():
    """Main function to play the word guessing game."""
    while True:
        print("\nStart the guessing game? (y/n)")
        user_choice = input().lower()
        
        if user_choice == 'n':
            print("Thanks for playing!")
            sys.exit(0)
        elif user_choice == 'y':
            print("Enter a word to start the guess (or press Enter to generate a random word):")
            user_word = input().strip().lower()
            
            # Use user's word or generate a random one
            if user_word:
                guess_word = user_word
            else:
                guess_word = generate_initial_word()
                print(f"Generated initial word: {guess_word}")
            
            # Initialize game state
            word_length = len(guess_word)
            seed = random.randint(1, 10000)
            guess_count = 1
            previous_guesses = [guess_word]
            
            # Initialize tracking dictionaries at the game level
            absent_letters = set()
            present_letters = {}  # {letter: [positions where it's present]}
            correct_letters = {}  # {position: letter}
            letter_constraints = {}  # {letter: min_count}
            
            # Game loop
            while True:
                # Call API with the guess
                response = call_api(guess_word, seed)
                if response is None:
                    print("Failed to get response from API. Please try again.")
                    break
                
                # Analyze response and update tracking dictionaries
                correct_percentage = analyze_response(
                    response, 
                    word_length, 
                    absent_letters, 
                    present_letters, 
                    correct_letters, 
                    letter_constraints
                )
                
                # Display results
                print(f"\nGuess #{guess_count}: {guess_word}")
                # print(f"API Response: {response}")
                print(f"Absent: {', '.join(sorted(absent_letters))}")
                print(f"Present: {', '.join(sorted(present_letters.keys()))}")
                print(f"Correct: {', '.join([correct_letters[i] for i in sorted(correct_letters.keys())])}")
                print(f"Correct Percentage: {correct_percentage:.1f}%")
                
                # Check if the guess is correct
                if correct_percentage == 100:
                    print(f"\nWord \"{guess_word}\" is correct and guessed in {guess_count} guesses.")
                    break
                
                # Generate next word
                guess_word = generate_next_word(
                    word_length, 
                    absent_letters, 
                    present_letters, 
                    correct_letters, 
                    letter_constraints, 
                    previous_guesses
                )
                previous_guesses.append(guess_word)
                guess_count += 1
        else:
            print("Invalid input. Please enter 'y' or 'n'.")

if __name__ == "__main__":
    try:
        play_guessing_game()
    except KeyboardInterrupt:
        print("\nGame interrupted. Exiting...")
    except Exception as e:
        print(f"An error occurred: {e}")