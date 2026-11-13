-- Let established campaign/Codex history sync without truncating local player data.
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
  if octet_length(campaign::text) > 48000 then
    raise exception 'campaign projection is too large' using errcode = '22023';
  end if;

  allowed := array['learning_state','streak','skills','stats','achievements','goals','projects','current_quest','codex','dungeon_run','dungeon_leaderboard','dungeon_journal','practice_sessions'];
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
    if jsonb_typeof(item) <> 'object' or (item - array['status','run_id','seed','class_id','concept_id','region_id','floor','room','room_type','score','run_coins','started_at','updated_at','ended_at','loadout','inventory','question','question_number','room_choices','map','floor_layout','gear_charge','gear_charge_weapon','gear_revive_used','gear_first_miss_floor','risk_profile','risk_status','editor_content','last_result','history','attempts']) <> '{}'::jsonb then
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
    if item ? 'region_id' and jsonb_typeof(item -> 'region_id') <> 'null'
       and (jsonb_typeof(item -> 'region_id') <> 'string' or char_length(item ->> 'region_id') > 120) then
      raise exception 'dungeon region must be bounded text' using errcode = '22023';
    end if;
    if item ? 'floor_layout' and (jsonb_typeof(item -> 'floor_layout') <> 'string' or item ->> 'floor_layout' not in ('grid','lanes')) then
      raise exception 'dungeon floor layout is invalid' using errcode = '22023';
    end if;
    if item ? 'gear_charge' and (jsonb_typeof(item -> 'gear_charge') <> 'number' or (item ->> 'gear_charge')::numeric < 0 or (item ->> 'gear_charge')::numeric > 10) then
      raise exception 'dungeon gear charge is invalid' using errcode = '22023';
    end if;
    if item ? 'gear_charge_weapon' and jsonb_typeof(item -> 'gear_charge_weapon') <> 'null'
       and (jsonb_typeof(item -> 'gear_charge_weapon') <> 'string' or char_length(item ->> 'gear_charge_weapon') > 120) then
      raise exception 'dungeon charged weapon must be bounded text' using errcode = '22023';
    end if;
    if item ? 'gear_revive_used' and jsonb_typeof(item -> 'gear_revive_used') <> 'boolean' then
      raise exception 'dungeon revive flag must be boolean' using errcode = '22023';
    end if;
    if item ? 'gear_first_miss_floor' and (jsonb_typeof(item -> 'gear_first_miss_floor') <> 'number' or (item ->> 'gear_first_miss_floor')::numeric < 0 or (item ->> 'gear_first_miss_floor')::numeric > 1000000) then
      raise exception 'dungeon first-miss floor is invalid' using errcode = '22023';
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
         or ((item -> 'map') - array['floor','revealed','current_node_id','visited_node_ids','nodes','edges']) <> '{}'::jsonb
         or octet_length((item -> 'map')::text) > 9000 then
        raise exception 'dungeon map contains unsupported fields' using errcode = '22023';
      end if;
      if (item -> 'map') ? 'revealed' and jsonb_typeof((item -> 'map') -> 'revealed') <> 'boolean' then
        raise exception 'dungeon map revealed flag must be boolean' using errcode = '22023';
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
  if campaign ? 'dungeon_journal' then
    item := campaign -> 'dungeon_journal';
    if jsonb_typeof(item) <> 'object' or (item - array['unlocks','cleared_bosses']) <> '{}'::jsonb then
      raise exception 'dungeon journal contains unsupported fields' using errcode = '22023';
    end if;
    if item ? 'unlocks' then
      if jsonb_typeof(item -> 'unlocks') <> 'array' or jsonb_array_length(item -> 'unlocks') > 128 then
        raise exception 'dungeon journal unlocks must be bounded' using errcode = '22023';
      end if;
      for field_name in select jsonb_array_elements_text(item -> 'unlocks') loop
        if field_name !~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$' then
          raise exception 'dungeon journal unlock is invalid' using errcode = '22023';
        end if;
      end loop;
    end if;
    if item ? 'cleared_bosses' then
      if jsonb_typeof(item -> 'cleared_bosses') <> 'array' or jsonb_array_length(item -> 'cleared_bosses') > 8 then
        raise exception 'dungeon journal boss clears must be bounded' using errcode = '22023';
      end if;
      for field_name in select jsonb_array_elements_text(item -> 'cleared_bosses') loop
        if field_name !~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$' then
          raise exception 'dungeon journal boss clear is invalid' using errcode = '22023';
        end if;
      end loop;
    end if;
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

-- Validate the compact Home ladder projection without weakening existing domain checks.
create or replace function public.validate_player_state_projection(next_state jsonb)
returns void
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  base_state jsonb;
  field_name text;
  item jsonb;
begin
  if next_state is null or jsonb_typeof(next_state) <> 'object' then
    raise exception 'next_state must be a JSON object' using errcode = '22023';
  end if;
  if octet_length(next_state::text) > 64000 then
    raise exception 'next_state is too large' using errcode = '22023';
  end if;
  if next_state ? 'campaign' then
    perform public.validate_campaign_projection(next_state -> 'campaign');
    base_state := next_state - 'campaign';
  else
    base_state := next_state;
  end if;

  -- Campaign gear inventories are bounded identifiers owned by the state
  -- service. The older primitive validator only knew the three equipped text
  -- fields, so validate the new lists here and strip them before delegation.
  if base_state ? 'equipment' and jsonb_typeof(base_state -> 'equipment') = 'object' then
    for field_name in select jsonb_object_keys(base_state -> 'equipment') loop
      if field_name in ('owned_armor', 'owned_trinkets') then
        if jsonb_typeof((base_state -> 'equipment') -> field_name) <> 'array'
           or jsonb_array_length((base_state -> 'equipment') -> field_name) > 24 then
          raise exception 'equipment inventory must be a bounded array' using errcode = '22023';
        end if;
        for item in select jsonb_array_elements((base_state -> 'equipment') -> field_name) loop
          if jsonb_typeof(item) <> 'string' or (item #>> '{}') !~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$' then
            raise exception 'equipment inventory entries must be safe identifiers' using errcode = '22023';
          end if;
        end loop;
      end if;
    end loop;
    base_state := jsonb_set(
      base_state,
      '{equipment}',
      (base_state -> 'equipment') - array['owned_armor', 'owned_trinkets']
    );
  end if;
  -- The new Home ladder and the older Home purchases share the same
  -- revision/CAS state. Validate every added field before the legacy validator.
  if base_state ? 'homestead' and jsonb_typeof(base_state -> 'homestead') = 'object' then
    if (base_state -> 'homestead') ? 'room_levels' then
      if jsonb_typeof(base_state -> 'homestead' -> 'room_levels') <> 'object' then
        raise exception 'room_levels must be an object' using errcode = '22023';
      end if;
      if (select count(*) from jsonb_object_keys(base_state -> 'homestead' -> 'room_levels')) <> 7 then
        raise exception 'room_levels must contain seven rooms' using errcode = '22023';
      end if;
      for field_name in select jsonb_object_keys(base_state -> 'homestead' -> 'room_levels') loop
        if not (field_name = any(array['great_hall','library','armory','pantry','gallery','war_room','den'])) then
          raise exception 'room_levels contains an unknown room' using errcode = '22023';
        end if;
        item := (base_state -> 'homestead' -> 'room_levels') -> field_name;
        if jsonb_typeof(item) <> 'number' or (item #>> '{}') !~ '^(0|[1-9][0-9]*)$' then
          raise exception 'room level must be a nonnegative integer' using errcode = '22023';
        end if;
        if (item #>> '{}')::numeric > (case when field_name = 'pantry' then 8 else 9 end) then
          raise exception 'room level exceeds its ladder' using errcode = '22023';
        end if;
      end loop;
    end if;
    if (base_state -> 'homestead') ? 'upgrade_tokens' then
      item := base_state -> 'homestead' -> 'upgrade_tokens';
      if jsonb_typeof(item) <> 'number' or (item #>> '{}') !~ '^(0|[1-9][0-9]*)$' then
        raise exception 'upgrade_tokens must be a nonnegative integer' using errcode = '22023';
      end if;
      if (item #>> '{}')::numeric > 1000000000 then
        raise exception 'upgrade_tokens exceeds the limit' using errcode = '22023';
      end if;
    end if;
    for field_name in select unnest(array['room_upgrades','market_purchases']) loop
      if (base_state -> 'homestead') ? field_name then
        item := (base_state -> 'homestead') -> field_name;
        if jsonb_typeof(item) <> 'array' then
          raise exception '% must be an array', field_name using errcode = '22023';
        end if;
        if jsonb_array_length(item) > (case when field_name = 'room_upgrades' then 5 else 11 end) then
          raise exception '% contains too many entries', field_name using errcode = '22023';
        end if;
        for item in select jsonb_array_elements((base_state -> 'homestead') -> field_name) loop
          if jsonb_typeof(item) <> 'string' or (item #>> '{}') !~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$' then
            raise exception '% contains an invalid identifier', field_name using errcode = '22023';
          end if;
          if field_name = 'room_upgrades' and not ((item #>> '{}') = any(array['reinforced-hearth','warding-loom','breaker-workbench','siphon-basin','field-kitchen'])) then
            raise exception 'room_upgrades contains an unknown upgrade' using errcode = '22023';
          end if;
          if field_name = 'market_purchases' and not ((item #>> '{}') = any(array['field-bandage','ember-tonic','camp-meal','debugger-plate','ledgerguard-coat','emberweave-mantle','syntax-ward','loop-lens','guard-bell','scimitar-of-momentum','vision-scroll'])) then
            raise exception 'market_purchases contains an unknown item' using errcode = '22023';
          end if;
        end loop;
      end if;
    end loop;
    if (base_state -> 'homestead') ? 'upgrade_effects' then
      if jsonb_typeof(base_state -> 'homestead' -> 'upgrade_effects') <> 'object' then
        raise exception 'upgrade_effects must be an object' using errcode = '22023';
      end if;
      for field_name in select jsonb_object_keys(base_state -> 'homestead' -> 'upgrade_effects') loop
        if not (field_name = any(array['max_hp_delta','failure_damage_reduction','resolve_impact_delta','guard_break_heal','meal_heal_delta'])) then
          raise exception 'upgrade_effects contains an unknown field' using errcode = '22023';
        end if;
        item := (base_state -> 'homestead' -> 'upgrade_effects') -> field_name;
        if jsonb_typeof(item) <> 'number' or (item #>> '{}') !~ '^(0|[1-9][0-9]*)$' then
          raise exception 'upgrade effect must be a nonnegative integer' using errcode = '22023';
        end if;
        if (item #>> '{}')::numeric > 1000000000 then
          raise exception 'upgrade effect exceeds the limit' using errcode = '22023';
        end if;
      end loop;
    end if;
    base_state := jsonb_set(base_state, '{homestead}',
      (base_state -> 'homestead') - array['room_levels','upgrade_tokens','room_upgrades','upgrade_effects','market_purchases']);
  end if;
  perform public.validate_player_state_projection_base(base_state);
end;
$$;

revoke all on function public.validate_player_state_projection(jsonb) from public;


-- Preserve the existing row bound while allowing the now-bounded campaign history.
alter table public.player_state
  drop constraint if exists player_state_state_size;
alter table public.player_state
  add constraint player_state_state_size
  check (octet_length(state::text) <= 64000) not valid;
alter table public.player_state
  validate constraint player_state_state_size;
