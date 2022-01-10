import json
import os
import re

class RaceDataset():
    def __init__(self,split_set,level,dataset_dir='datasets/RACE',no_label=False):
        super().__init__()
        assert split_set in ['dev','test','train']
        assert level in ['all','middle','high']
        self.all_file_paths = []
        for root, dirs, files in os.walk(os.path.join(dataset_dir,split_set)):
            for f in files:
                if level == 'all':
                    self.all_file_paths.append(os.path.join(root,f))
                elif root == os.path.join(dataset_dir,split_set,level):
                    self.all_file_paths.append(os.path.join(root,f))
            
    def __getitem__(self,index):
        with open(self.all_file_paths[index],'r',encoding='utf-8') as f:
            data = json.load(f)
            return data
            
    def __len__(self):
        return len(self.all_file_paths)

def gen_match_key(question:str):
    return question.lower().replace(" ","")[8:-1]

if __name__ == "__main__":
    splits = ['dev','test','train']
    levels = ['high','middle']

    g_type_keywords = open('g_type_keywords.txt','r',encoding='utf-8').read().strip().split('\n')
    for i in range(len(g_type_keywords)):
        g_type_keywords[i] = '.*' + g_type_keywords[i] + '.*'
    g_type_keywords_reg_rule = r"|".join(g_type_keywords)

    output_dir = 'datasets/qgg-dataset'
    os.system('rm -rf %s'%output_dir)
    os.makedirs(output_dir,exist_ok=True)

    for split in splits:
        # count 
        match_count = 0
        step = 0
        total = 0
        
        #
        eqg_race_plus_dir = os.path.join(output_dir,split)
        os.makedirs(eqg_race_plus_dir,exist_ok=True)
        eqg_race = open(os.path.join('datasets/EQG-RACE',split+'.json'),'r',encoding='utf-8')
        eqg_race = json.load(eqg_race)
        total += len(eqg_race)

        summarization_type_question_count = 0        
        factiod_type_question_count = 0
        cloze_type_question_count = 0
        
        for level in levels:            
            race_dataset = RaceDataset(split,level)
            with open(os.path.join(eqg_race_plus_dir,level+'.jsonl'),'a') as merge_race_f:
                for race_data in race_dataset:
                    race_questions = race_data['questions'][:]
                    race_data['factiod_questions'] = []
                    race_data['cloze_questions'] = []
                    race_data['summarization_questions'] = []

                    # cloze_questions
                    for race_question in race_questions[:]:
                        if re.search('_',race_question):                            
                            #
                            if re.match(g_type_keywords_reg_rule,race_question.lower()) is not None:
                                # print(race_question)
                                summarization_type_question_count += 1
                                race_data['summarization_questions'].append(race_question)
                            else:
                                cloze_type_question_count +=1
                                race_data['cloze_questions'].append(race_question)
                            race_questions.remove(race_question)
                                                    
                    # specific_questions
                    for race_question in race_questions[:]:
                        race_question_key = gen_match_key(race_question)

                        for eqg_i,eqg_race_data in enumerate(eqg_race): # dict_keys(['question', 'max_sent', 'tag', 'rouge', 'answer', 'sent'])
                            eqg_race_question_key = gen_match_key(eqg_race_data['question'])

                            if race_question_key == eqg_race_question_key:                                
                                #
                                if re.match(g_type_keywords_reg_rule,race_question.lower()) is not None: 
                                    # print(race_question)
                                    summarization_type_question_count += 1
                                    race_data['summarization_questions'].append(race_question)
                                else:
                                    factiod_type_question_count += 1
                                    race_data['factiod_questions'].append(race_question)
                                eqg_race.remove(eqg_race_data)

                                try:
                                    race_questions.remove(race_question)
                                except:
                                    pass
                                match_count += 1

                            step+=1
                            if step%5000==0:                                
                                print('%3.2f'%(match_count/total*100),'match_count(miss_match): %d/%d(%d)'%(match_count,total,total-match_count),'step:',str(step/1000)+'k',"{:<50}".format(merge_race_f.name),end='\r')
                    
                    # general_questions
                    race_data['general_questions'] = race_questions

                    # clean repeat data
                    for key in race_data.keys():
                        try:
                            if type(race_data[key]) == list and key in ['factiod_questions','cloze_questions','summarization_questions','general_questions']:
                                race_data[key] = list(set(race_data[key]))                                
                        except:
                            pass
                    del race_data['general_questions']                    
                    merge_race_f.write(json.dumps(race_data)+'\n')        
        print(split,'%3.2f'%(match_count/total*100),
            'match_count(miss_match): %d/%d(%d)'%(match_count,total,total-match_count),
            "cloze_type:%d"%(cloze_type_question_count),
            "factiod_type:%d"%(factiod_type_question_count),            
            "summarization_type:%d"%(summarization_type_question_count),
            " "*60
            ,end='\n')
        