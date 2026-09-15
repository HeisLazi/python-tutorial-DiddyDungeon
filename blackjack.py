#### 1. Import & Card Pool                                      
                                                                  
    import random                                                 
                                                                  
    cards = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]          
                                                                  
  #### 2. Deal Function or Random Helper                          
                                                                  
    def deal_card():                                              
        return random.choice(cards)                               
                                                                  
  #### 3. Initial Deal & Score Helper                             
                                                                  
    player_hand = [deal_card(), deal_card()]                      
    dealer_hand = [deal_card(), deal_card()]                      
                                                                  
    def calculate_score(hand):                                    
        return sum(hand) 