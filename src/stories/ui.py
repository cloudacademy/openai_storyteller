from stories import app

import streamlit as st

st.set_page_config(
    page_title='Interactive Storyteller',
    page_icon='📖',
    layout='wide',
)

###############################################################################
# Helper Functions
###############################################################################
def update_session_name(session_id):
    story_app.sessions[session_id].name = st.session_state[f'{session_id}_name']
    story_app.save()


###############################################################################
# The Story App
###############################################################################
@st.cache_resource
def cached_story_app(pre_load=True):
    story = app.InteractiveStories()
    
    if pre_load:    
        story.load()
    return story
    

def init_app():
    if 'app' not in st.session_state:
        st.session_state.app = cached_story_app()
    return st.session_state.app

# This is a global variable that will be initialized on the first run.
story_app = init_app()


with st.sidebar:
    st.subheader('Story Sessions')
    ###############################################################################
    # New Session
    ###############################################################################
    st.button('New Session', use_container_width=True, on_click=story_app.activate_session)
    ###############################################################################
    # Sessions
    ###############################################################################
    for session in story_app.sessions:
        st.divider()

        name_key = f'{session.id}_name'
        edit_key = f'{session.id}_edit'
        load_key = f'{session.id}_load'
        cull_key = f'{session.id}_cull'

        if edit_key in st.session_state and st.session_state[edit_key]:
            st.text_input('Session Name', session.friendly_name, key=name_key, on_change=update_session_name, args=(session.id,), label_visibility='collapsed')
        else:
            st.subheader(session.friendly_name)
            
        a, b, c = st.columns(3)

        with a:
            st.toggle('✏️ Edit', key=edit_key)

        with b:
            st.button('⚙️ Load', key=load_key, on_click=story_app.activate_session, args=(session.id, ))
                
        with c:
            st.button('🗑️ Cull', key=cull_key, on_click=story_app.delete_session, args=(session.id, ))

    ###############################################################################
    # Narrator Voice
    ###############################################################################
    st.divider()
    st.subheader('Narration Settings')
    st.selectbox('Voice', 'alloy echo fable onyx nova shimmer'.split(), index=4, key='narrator_voice')
    st.selectbox('Model', 'tts-1 tts-1-hd'.split(), index=0, key='narrator_model')

    ###############################################################################
    # Image Generator
    ###############################################################################
    def update_image_settings():
        story_app.image_args.model = st.session_state.image_model
        story_app.image_args.quality = st.session_state.image_quality
        story_app.image_args.size = st.session_state.image_size
        story_app.image_args.style = st.session_state.image_style

    st.divider()
    st.subheader('Image Settings')
    st.selectbox('Model', 'dall-e-2 dall-e-3'.split(), index=1, key='image_model', on_change=update_image_settings)
    # The quality, size, and style options depend on the model.
    if st.session_state.image_model == 'dall-e-3':
        st.selectbox('Quality', 'standard hd'.split(), index=0, key='image_quality', on_change=update_image_settings)
        st.selectbox('Size', '1024x1024 1792x1024 1024x1792'.split(), index=0, key='image_size', on_change=update_image_settings)
        st.selectbox('Style', 'vivid natural'.split(), index=0, key='image_style', on_change=update_image_settings)
    else:
        st.selectbox('Size', '256x256 512x512 1024x1024'.split(), index=2, key='image_size', on_change=update_image_settings)
    

    ###############################################################################
    # Update Assistant
    ###############################################################################
    st.divider()
    st.subheader('Assistant Settings')
    st.button('Update', on_click=story_app.update_assistant, use_container_width=True)


###############################################################################
# The primary content area.
# A multi-tab layout with the following tabs: Story, Entities, Developer Log.
###############################################################################

###############################################################################
# Chat Input
###############################################################################
if (prompt := st.chat_input('What would you like to do?')):
    story_app.prompt_and_wait(prompt)

a, b, c = st.tabs(['Story', 'Entities', 'Developer Log'])
###############################################################################
# Story Tab
###############################################################################
with a:
    try:
        if not story_app.messages:
            st.markdown(story_app.welcome())

        for message in story_app.messages:
            id, text, role = message.id, message.text, message.role

            with st.chat_message(role):
                st.markdown(text)

                if narration := story_app.asset(id, 'narration'):
                    st.audio(
                        narration.content, 
                        format='audio/opus'
                    )
                else:
                    st.button(
                        '🔊 Create Narration', 
                        key=f'{id}_narration', 
                        on_click=story_app.get_narration, 
                        args=(id, text),
                        kwargs={
                            'voice': st.session_state.narrator_voice,
                            'model': st.session_state.narrator_model,
                        }
                    )
                    
                if visualization := story_app.asset(id, 'visualization', 'png'):
                    st.image(visualization.content)
    except Exception as e:
        st.error(e)
    
###############################################################################
# Entities Tab
###############################################################################
with b:
    # Show the session info.
    st.markdown(story_app.sessinfo())

    for entity in story_app.entities:
        st.divider()
        name, type, desc = entity.name, entity.type, entity.desc
        nkey, tkey, dkey = f'{name}_name', f'{name}_type', f'{name}_desc'

        st.text_input('Name', name, key=nkey)
        st.text_input('Type', type, key=tkey)
        st.text_area( 'Desc', desc, key=dkey)

        if st.button('Update', key=f'{name}_update'):
            story_app.entities[name] = app.Entity(
                name=st.session_state[nkey],
                type=st.session_state[tkey],
                desc=st.session_state[dkey],
            )
            # Save the updated entity.
            story_app.save()

###############################################################################
# Developer Log Tab
###############################################################################
with c:
    # Combine the action log into a single string.
    actions = '\n'.join(story_app.action_log)
    # Format the string as a code block.
    actions = f'```\n{actions}\n```'
    # Display the formatted string.
    st.markdown(actions)

