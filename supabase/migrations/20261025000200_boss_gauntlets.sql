-- Each campaign boss now has its own gauntlet of up to eight phases (an early
-- boss three, a late boss six or seven). Allow the new phase ids and the
-- longer verified list. Every other check is unchanged.

create or replace function public.validate_campaign_projection(campaign jsonb)
returns void
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  key_name text;
  field_name text;
  item jsonb;
  mob_item jsonb;
  allowed text[];
begin
  if campaign is null or jsonb_typeof(campaign) <> 'object' then
    raise exception 'campaign projection must be an object' using errcode = '22023';
  end if;
  if octet_length(campaign::text) > 18000 then
    raise exception 'campaign projection is too large' using errcode = '22023';
  end if;

  allowed := array['learning_state','streak','skills','stats','achievements','goals','projects','current_quest','codex','dungeon_run','dungeon_leaderboard','practice_sessions'];
  for key_name in select jsonb_object_keys(campaign) loop
    if not (key_name = any(allowed)) then
      raise exception 'campaign projection contains unsupported domains' using errcode = '22023';
    end if;
    if key_name = 'current_quest' then
      if jsonb_typeof(campaign -> key_name) <> 'string' or char_length(campaign ->> key_name) > 400 then
        raise exception 'current_quest must be bounded text' using errcode = '22023';
      end if;
    elsif key_name = 'dungeon_run' and jsonb_typeof(campaign -> key_name) = 'null' then
      null;
    elsif key_name = any(array['skills','achievements','projects','dungeon_leaderboard','practice_sessions']) then
      if jsonb_typeof(campaign -> key_name) <> 'array' then
        raise exception '% campaign domain must be an array', key_name using errcode = '22023';
      end if;
    elsif jsonb_typeof(campaign -> key_name) <> 'object' then
      raise exception '% campaign domain must be an object', key_name using errcode = '22023';
    end if;
  end loop;

  if campaign ? 'learning_state' then
    allowed := array['project','concept','phase','reference_mode','clean_clear_eligible'];
    for field_name in select jsonb_object_keys(campaign -> 'learning_state') loop
      if not (field_name = any(allowed)) then
        raise exception 'learning_state contains unsupported fields' using errcode = '22023';
      end if;
    end loop;
  end if;
  if campaign ? 'streak' then
    allowed := array['current','longest','last_active','freeze_tokens','days_logged'];
    for field_name in select jsonb_object_keys(campaign -> 'streak') loop
      if not (field_name = any(allowed)) then
        raise exception 'streak contains unsupported fields' using errcode = '22023';
      end if;
    end loop;
    if campaign -> 'streak' ? 'days_logged' and
       (jsonb_typeof((campaign -> 'streak') -> 'days_logged') <> 'array' or jsonb_array_length((campaign -> 'streak') -> 'days_logged') > 100) then
      raise exception 'days_logged must be a bounded array' using errcode = '22023';
    end if;
  end if;

  if campaign ? 'skills' then
    if jsonb_array_length(campaign -> 'skills') > 50 then
      raise exception 'skills must be a bounded array' using errcode = '22023';
    end if;
    for item in select jsonb_array_elements(campaign -> 'skills') loop
      if jsonb_typeof(item) <> 'object' or (item - array['name','concept','status','evidence','interview_passes','shield']) <> '{}'::jsonb then
        raise exception 'skill projection contains unsupported fields' using errcode = '22023';
      end if;
      if item ? 'shield' and (jsonb_typeof(item -> 'shield') <> 'object' or ((item -> 'shield') - array['tier','charges','max_charges']) <> '{}'::jsonb) then
        raise exception 'skill shield projection contains unsupported fields' using errcode = '22023';
      end if;
    end loop;
  end if;

  if campaign ? 'stats' then
    allowed := array['sessions','projects_cleared','bosses_defeated','mobs_defeated','interviews_passed','interviews_failed','mastery_shields_earned','bugs_fixed','explanations','clean_clears','commits_logged','reference_mode_uses','guided_milestones','recovery_trials_passed','creative_bonuses','discoveries_unlocked'];
    for field_name in select jsonb_object_keys(campaign -> 'stats') loop
      if not (field_name = any(allowed)) then
        raise exception 'stats contains unsupported fields' using errcode = '22023';
      end if;
    end loop;
  end if;

  if campaign ? 'achievements' then
    if jsonb_array_length(campaign -> 'achievements') > 100 then
      raise exception 'achievements must be a bounded array' using errcode = '22023';
    end if;
    for item in select jsonb_array_elements(campaign -> 'achievements') loop
      if jsonb_typeof(item) <> 'object' or (item - array['name','description','unlocked']) <> '{}'::jsonb then
        raise exception 'achievement projection contains unsupported fields' using errcode = '22023';
      end if;
    end loop;
  end if;

  if campaign ? 'goals' then
    allowed := array['daily','weekly','long_term'];
    for field_name in select jsonb_object_keys(campaign -> 'goals') loop
      if not (field_name = any(allowed)) or jsonb_typeof((campaign -> 'goals') -> field_name) <> 'array' or jsonb_array_length((campaign -> 'goals') -> field_name) > 20 then
        raise exception 'goals contains an unsupported or unbounded bucket' using errcode = '22023';
      end if;
      for item in select jsonb_array_elements((campaign -> 'goals') -> field_name) loop
        if jsonb_typeof(item) <> 'object' or (item - array['id','text','target','progress','reward_xp','reward_coins','done']) <> '{}'::jsonb then
          raise exception 'goal projection contains unsupported fields' using errcode = '22023';
        end if;
      end loop;
    end loop;
  end if;

  if campaign ? 'projects' then
    if jsonb_array_length(campaign -> 'projects') > 20 then
      raise exception 'projects must be a bounded array' using errcode = '22023';
    end if;
    for item in select jsonb_array_elements(campaign -> 'projects') loop
      if jsonb_typeof(item) <> 'object' or (item - array['order','branch','name','status','progress','boss','boss_status','clean_clear_eligible','completed','completed_at','clean_clear','mob_sequence_complete','creative_discoveries','boss_validation','mobs']) <> '{}'::jsonb then
        raise exception 'project projection contains unsupported fields' using errcode = '22023';
      end if;
      if item ? 'boss_validation' then
        if jsonb_typeof(item -> 'boss_validation') <> 'object' or ((item -> 'boss_validation') - array['verified','history','completed_at']) <> '{}'::jsonb then
          raise exception 'boss validation projection contains unsupported fields' using errcode = '22023';
        end if;
        if item -> 'boss_validation' ? 'verified' then
          if jsonb_typeof((item -> 'boss_validation') -> 'verified') <> 'array' or jsonb_array_length((item -> 'boss_validation') -> 'verified') > 8 then
            raise exception 'boss validation phases must be a bounded array' using errcode = '22023';
          end if;
          for field_name in select jsonb_array_elements_text((item -> 'boss_validation') -> 'verified') loop
            if field_name not in ('required_behavior', 'explanation', 'edge_cases', 'twist_2', 'twist_3', 'twist_4', 'read_2', 'interview') then
              raise exception 'boss validation contains an unsupported phase' using errcode = '22023';
            end if;
          end loop;
        end if;
        if item -> 'boss_validation' ? 'history' then
          if jsonb_typeof((item -> 'boss_validation') -> 'history') <> 'array' or jsonb_array_length((item -> 'boss_validation') -> 'history') > 20 then
            raise exception 'boss validation history must be bounded' using errcode = '22023';
          end if;
          for mob_item in select jsonb_array_elements((item -> 'boss_validation') -> 'history') loop
            if jsonb_typeof(mob_item) <> 'object' or (mob_item - array['requirement_id','evidence_id','reason','recorded_at']) <> '{}'::jsonb then
              raise exception 'boss validation history contains unsupported fields' using errcode = '22023';
            end if;
          end loop;
        end if;
      end if;
      if item ? 'mobs' then
        if jsonb_typeof(item -> 'mobs') <> 'array' or jsonb_array_length(item -> 'mobs') > 20 then
          raise exception 'project mobs must be a bounded array' using errcode = '22023';
        end if;
        for mob_item in select jsonb_array_elements(item -> 'mobs') loop
          if jsonb_typeof(mob_item) <> 'object' or (mob_item - array['name','status','assist','concept','encounter','max_resolve','resolve','impact_applied','objective_attempts']) <> '{}'::jsonb then
            raise exception 'mob projection contains unsupported fields' using errcode = '22023';
          end if;
        end loop;
      end if;
    end loop;
  end if;

  if campaign ? 'codex' then
    if (campaign -> 'codex') - array['encounters'] <> '{}'::jsonb or jsonb_typeof((campaign -> 'codex') -> 'encounters') <> 'array' or jsonb_array_length((campaign -> 'codex') -> 'encounters') > 100 then
      raise exception 'codex projection is invalid or unbounded' using errcode = '22023';
    end if;
    for item in select jsonb_array_elements((campaign -> 'codex') -> 'encounters') loop
      if jsonb_typeof(item) <> 'object' or (item - array['id','project_id','mob_name','concept','status','question_types','weaknesses','notes','player_notes','attempts','results','interview_history','mastery']) <> '{}'::jsonb then
        raise exception 'codex encounter contains unsupported fields' using errcode = '22023';
      end if;
      if item ? 'player_notes' and (jsonb_typeof(item -> 'player_notes') <> 'array' or jsonb_array_length(item -> 'player_notes') > 20) then
        raise exception 'codex player notes must be bounded' using errcode = '22023';
      end if;
      if item ? 'results' and (jsonb_typeof(item -> 'results') <> 'array' or jsonb_array_length(item -> 'results') > 20) then
        raise exception 'codex results must be bounded' using errcode = '22023';
      end if;
      if item ? 'interview_history' and (jsonb_typeof(item -> 'interview_history') <> 'array' or jsonb_array_length(item -> 'interview_history') > 20) then
        raise exception 'codex interview history must be bounded' using errcode = '22023';
      end if;
      if item ? 'mastery' and (jsonb_typeof(item -> 'mastery') <> 'object' or ((item -> 'mastery') - array['evidence','interview_passes','shield','tier','charges','max_charges']) <> '{}'::jsonb) then
        raise exception 'codex mastery contains unsupported fields' using errcode = '22023';
      end if;
    end loop;
  end if;

  if campaign ? 'dungeon_run' and jsonb_typeof(campaign -> 'dungeon_run') <> 'null' then
    item := campaign -> 'dungeon_run';
    if jsonb_typeof(item) <> 'object' or (item - array['status','run_id','seed','class_id','concept_id','floor','room','room_type','score','run_coins','started_at','updated_at','ended_at','loadout','inventory','question','question_number','room_choices','map','risk_profile','risk_status','editor_content','last_result','history','attempts']) <> '{}'::jsonb then
      raise exception 'dungeon_run contains unsupported fields' using errcode = '22023';
    end if;
    if item ? 'editor_content' and octet_length(item ->> 'editor_content') > 8000 then
      raise exception 'dungeon editor checkpoint is too large' using errcode = '22023';
    end if;
    if item ? 'inventory' then
      if jsonb_typeof(item -> 'inventory') <> 'array' or jsonb_array_length(item -> 'inventory') > 24 then
        raise exception 'dungeon inventory must be a bounded array' using errcode = '22023';
      end if;
      for mob_item in select jsonb_array_elements(item -> 'inventory') loop
        if jsonb_typeof(mob_item) <> 'object' or (mob_item - array['id','name','kind','armor','trinket','description']) <> '{}'::jsonb then
          raise exception 'dungeon inventory contains unsupported fields' using errcode = '22023';
        end if;
      end loop;
    end if;
    if item ? 'question' and jsonb_typeof(item -> 'question') <> 'null' and ((item -> 'question') - array['id','question_type','concept_id','difficulty','prompt','options']) <> '{}'::jsonb then
      raise exception 'dungeon question contains unsupported or hidden fields' using errcode = '22023';
    end if;
    if item ? 'room_choices' and (jsonb_typeof(item -> 'room_choices') <> 'array' or jsonb_array_length(item -> 'room_choices') > 3) then
      raise exception 'dungeon room choices must be bounded' using errcode = '22023';
    end if;
    if item ? 'history' and (jsonb_typeof(item -> 'history') <> 'array' or jsonb_array_length(item -> 'history') > 50) then
      raise exception 'dungeon history must be bounded' using errcode = '22023';
    end if;
    if item ? 'class_id' and jsonb_typeof(item -> 'class_id') <> 'null'
       and (jsonb_typeof(item -> 'class_id') <> 'string' or char_length(item ->> 'class_id') > 120) then
      raise exception 'dungeon class must be bounded text' using errcode = '22023';
    end if;
    if item ? 'risk_status' and jsonb_typeof(item -> 'risk_status') <> 'null'
       and (jsonb_typeof(item -> 'risk_status') <> 'string' or char_length(item ->> 'risk_status') > 120) then
      raise exception 'dungeon risk status must be bounded text' using errcode = '22023';
    end if;
    if item ? 'risk_profile' and jsonb_typeof(item -> 'risk_profile') <> 'null' then
      if jsonb_typeof(item -> 'risk_profile') <> 'object'
         or ((item -> 'risk_profile') - array['kind','room_type','title','preview']) <> '{}'::jsonb
         or octet_length((item -> 'risk_profile')::text) > 1400 then
        raise exception 'dungeon risk profile contains unsupported fields' using errcode = '22023';
      end if;
    end if;
    if item ? 'map' and jsonb_typeof(item -> 'map') <> 'null' then
      if jsonb_typeof(item -> 'map') <> 'object'
         or ((item -> 'map') - array['floor','current_node_id','visited_node_ids','nodes','edges']) <> '{}'::jsonb
         or octet_length((item -> 'map')::text) > 9000 then
        raise exception 'dungeon map contains unsupported fields' using errcode = '22023';
      end if;
      if (item -> 'map') ? 'nodes' then
        if jsonb_typeof((item -> 'map') -> 'nodes') <> 'array' or jsonb_array_length((item -> 'map') -> 'nodes') > 64 then
          raise exception 'dungeon map nodes must be bounded' using errcode = '22023';
        end if;
        for mob_item in select jsonb_array_elements((item -> 'map') -> 'nodes') loop
          if jsonb_typeof(mob_item) <> 'object' or (mob_item - array['id','type','row','column','label','note']) <> '{}'::jsonb then
            raise exception 'dungeon map node contains unsupported fields' using errcode = '22023';
          end if;
        end loop;
      end if;
      if (item -> 'map') ? 'visited_node_ids'
         and (jsonb_typeof((item -> 'map') -> 'visited_node_ids') <> 'array' or jsonb_array_length((item -> 'map') -> 'visited_node_ids') > 64) then
        raise exception 'dungeon map visits must be bounded' using errcode = '22023';
      end if;
      if (item -> 'map') ? 'edges' then
        if jsonb_typeof((item -> 'map') -> 'edges') <> 'object'
           or (select count(*) from jsonb_object_keys((item -> 'map') -> 'edges')) > 64 then
          raise exception 'dungeon map edges must be bounded' using errcode = '22023';
        end if;
        for mob_item in select value from jsonb_each((item -> 'map') -> 'edges') loop
          if jsonb_typeof(mob_item) <> 'array' or jsonb_array_length(mob_item) > 8 then
            raise exception 'dungeon map edges must be bounded' using errcode = '22023';
          end if;
        end loop;
      end if;
    end if;
  end if;

  if campaign ? 'dungeon_leaderboard' and jsonb_array_length(campaign -> 'dungeon_leaderboard') > 50 then
    raise exception 'dungeon leaderboard must be bounded' using errcode = '22023';
  end if;
  if campaign ? 'practice_sessions' then
    if jsonb_array_length(campaign -> 'practice_sessions') > 50 then
      raise exception 'practice sessions must be bounded' using errcode = '22023';
    end if;
    for item in select jsonb_array_elements(campaign -> 'practice_sessions') loop
      if jsonb_typeof(item) <> 'object' or (item - array['session_id','concept','question_type','difficulty','status','attempts','correct','started_at','updated_at','history']) <> '{}'::jsonb then
        raise exception 'practice session contains unsupported fields' using errcode = '22023';
      end if;
      if item ? 'history' and (jsonb_typeof(item -> 'history') <> 'array' or jsonb_array_length(item -> 'history') > 20) then
        raise exception 'practice history must be bounded' using errcode = '22023';
      end if;
    end loop;
  end if;
end;
$$;

revoke all on function public.validate_campaign_projection(jsonb) from public;
