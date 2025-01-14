from dash import Output, Input, html, State, MATCH, ALL, dcc, Dash, callback_context
from dash.exceptions import PreventUpdate
import pandas as pd

import dash_bootstrap_components as dbc

from EmojiFinder import EmojiFinderSql, SKIN_TONE_SUFFIXES
from pathlib import Path

parent_dir = Path().absolute().stem

e = EmojiFinderSql()

app = Dash(__name__,
           url_base_pathname=f"/dash/{parent_dir}/",
           external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
           title="Emoji Semantic Search",
           meta_tags=[
               {
                   "name": "viewport",
                   "content": "width=device-width, initial-scale=1"
               },
           ])
server = app.server
STYLE = {"marginBottom": 20, "marginTop": 20, 'width': '85%'}

range_slider = html.Div(
    [
        dbc.Label("Font Size", html_for="font-size-slider"),
        dcc.Slider(id="font-size-slider",
                   min=1,
                   max=4,
                   step=.5,
                   value=3,
                   persistence=True),
    ],
    className="mb-3",
)

tab1_content = dbc.Container(children=[
    html.H3('Emoji Semantic Search', style={'text-align': 'center'}),
    dbc.Container(
        [dbc.InputGroup([
            dbc.InputGroupText(
                html.I(className="bi bi-search", style={'float': 'left'})),
            dbc.Input(
                id='search-input',
                value='',
                debounce=True,
                autofocus=True,
                placeholder='Search for emoji (mostly limited to single words; or try an emoji like 🎟️)',
            ),
        ],
            style={'margin-top': '20px', 'margin-bottom': '20px'}),
            dbc.Button('Settings',
                       id='expand-prefs',
                       class_name='btn-secondary btn-sm',
                       style={'margin-top': '20px', 'margin-bottom': '20px'}),
        ],
        style={'display': 'flex', "gap": "20px", }
    ),


    dbc.Collapse([
        range_slider,
        dcc.Dropdown(id='skin-tone',
                     options=SKIN_TONE_SUFFIXES,
                     persistence=True,
                     placeholder='Skin Tone search priority...'),
        dcc.Dropdown(id='gender',
                     options=['man', 'woman', 'person'],
                     persistence=True,
                     placeholder="Gender search priority..."),
    ],
        id='search-priorities',
        is_open=False),
    html.Div(id='results'),
    dcc.Markdown(
        "Source code and more info on [Github](https://github.com/astrowonk/emoji_finder)."
    )
],
    style=STYLE)

tab2_content = dbc.Row([
    dbc.Col(
        dcc.Graph(
            id='my-graph',
            style={
                #     'width': '120vh',
                'height': '80vh'
            },
        )),
    dbc.Col(html.Div(id='emoji-result',
                     style={
                         'top': '50%',
                         'transform': 'translateY(-50%)',
                         'position': 'absolute',
                     }),
            width=1),
])

tab3_content = dcc.Markdown("""

Inspired ([nerd sniped?](https://xkcd.com/356/)) by [this post](https://data-folks.masto.host/@archie/109543055657581394) on Mastodon, I have created this effort to do semantic searching for emoji. So, you can search for `flower`, and also get `bouquet` 💐, and `cherry blossom` 🌸. (The iOS emoji keyboard does something similar, but this remains unavailable on MacOS.)

I'm using the python `sentence_tranformers` [package available from SBERT](https://www.sbert.net/index.html). This has a variety of [pretrained models suitable](https://www.sbert.net/docs/pretrained_models.htm) for the task of finding a semantic match between a search term and a target. I'm using the `all-mpnet-base-v2` model for the web apps.

In order to get this to run in a low memory environment of a web host, I *precompute semantic distance* against a corpus of common english words from [GloVe](https://nlp.stanford.edu/projects/glove/). This has the benefit of running with low memory on the web without pytorch, but the search only works for one-word searches. I may try to add command two-word phrases, but I imagine that data set would get large fast.

The `ComputeDistances` in `precompute.py` file writes to a sqlite database, which I think reduces memory usage. (It can also generate a series of .parquet files.)

The dash app also includes a 2D projection of the `sentence_transformer` vectors via [UMAP](https://umap-learn.readthedocs.io/en/latest/). This shows the emojis as they relate to each other semantically. This is limited to 750 emoji, but more will appear as one zooms in on the plotly graph. Clicking on an emoji will display it with a button to copy to the clipboard.

Source code, sqlitedb, etc. on [my emoji finder github repository](https://github.com/astrowonk/emoji_finder).

""",
                            style=STYLE)

tabs = dbc.Tabs([
    dbc.Tab(tab1_content, label="Search", tab_id='search-tab'),
    dbc.Tab(tab2_content, label="Graph", tab_id='graph-tab'),
    dbc.Tab(tab3_content, label='About')
],
    active_tab='search-tab')

app.layout = dbc.Container(tabs, style=STYLE)


def wrap_emoji(record, font_size):
    return html.Div(children=[
        html.P(record['emoji'],
               id=record['text'],
               style={'font-size': f'{font_size}em', 'margin-bottom': '0px'}),
        dcc.Clipboard(target_id=record['text'],
                      ),
    ],

        className='emoji',
        style={"display": "flex", "gap": "20px", "align-items": "center"})


def make_cell(item, skin_tone, gender, font_size):
    if not skin_tone:
        skin_tone = ''
    if not gender:
        gender = ''
    additional_emojis = e.add_variants(item['label'])
    additional_emojis = [{
        'emoji': e.emoji_dict[x]['emoji'],
        'text': e.emoji_dict[x]['text'],
        'label': x
    } for x in additional_emojis]
    priority_result = []
    gender_result = []
    if skin_tone:
        priority_result = [
            x for x in additional_emojis
            if x['label'].endswith(skin_tone + ':')
        ]
    if gender:
        gender_result = [
            x for x in priority_result or additional_emojis
            if x['label'].startswith(':' + gender)
        ]
    if gender_result:
        priority_result = gender_result

    if priority_result:
        priority_result = priority_result[0]
        #   print('PRIORITY')
        #   print(priority_result)
        #   print("ALL ADDITIONAL")
        #   print(additional_emojis)
        additional_emojis.remove(priority_result)
        target = priority_result
    else:
        target = item
    if additional_emojis:
        return [
            html.Div(
                children=[
                    html.Div(wrap_emoji(target, font_size)),
                    dbc.Button('More',
                               id={
                                   'type': 'more-button',
                                   'index': item['text']
                               },
                               className="btn-secondary btn-sm")
                ],
                style={'display': 'flex', "gap": "20px", "align-items": "center",
                       'justify-content': 'space-between', 'margin-right': '20pxx`'}

            ),
            dbc.Collapse(
                [wrap_emoji(item, font_size) for item in additional_emojis],
                id={
                    'type': 'more-emojis',
                    'index': item['text']
                },
                is_open=False)
        ]
    return wrap_emoji(item, font_size=font_size)


def make_table_row(record, skin_tone, gender, font_size):
    return html.Tr([
        html.Td(record['text'].title(), style={'vertical-align': 'middle'}),
        html.Td(make_cell(record, skin_tone, gender, font_size))
    ],
        style={'margin': 'auto'})


@app.callback(
    Output('results', 'children'),
    Input('search-input', 'value'),
    Input('skin-tone', 'value'),
    Input('gender', 'value'),
    Input('font-size-slider', 'value'),
)
def search_results(search, skin_tone, gender, font_size):
    if search:
        full_res = e.top_emojis(search)
        if full_res.empty:
            return html.H3('No Results')
        res_list = full_res.to_dict('records')
        variants = []
        for rec in res_list:
            variants.extend(e.add_variants(rec['label']))
        ## remove variants from list
        #full_res = full_res.query("label not in @variants")
        full_res['label'] = full_res['label'].apply(
            lambda x: y if (y := e.base_emoji_map.get(x)) else x)
        full_res = full_res.drop_duplicates(subset=['label'])
        table_header = [
            html.Thead(html.Tr([html.Th("Description"),
                                html.Th("Emoji")]))
        ]
        table_rows = [
            make_table_row(rec, skin_tone, gender, font_size)
            for rec in full_res.to_dict('records')
        ]
        table_body = [html.Tbody(table_rows)]
        return dbc.Table(table_header + table_body,
                         bordered=False,
                         striped=True)

    return html.H3('No Results')


@app.callback(
    Output({
        'type': 'more-emojis',
        'index': MATCH
    }, 'is_open'),
    State({
        'type': 'more-emojis',
        'index': MATCH
    }, 'is_open'),
    Input({
        'type': 'more-button',
        'index': MATCH
    }, 'n_clicks'),
)
def button_action(state, n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return not state


@app.callback(
    Output('search-priorities', 'is_open'),
    State('search-priorities', 'is_open'),
    Input('expand-prefs', 'n_clicks'),
)
def button_action(state, n_clicks):
    if not n_clicks:
        raise PreventUpdate
    return not state


@app.callback(
    Output('my-graph', 'figure'),
    Input('my-graph', 'relayoutData'),
)
def make_graph(data):
    print(data)

    x_min, x_max = -20.0, 20.0
    y_min, y_max = -20.0, 20.0
    if data is not None and data.get('xaxis.range[0]'):
        x_min, x_max = data['xaxis.range[0]'], data['xaxis.range[1]']
        y_min, y_max = data['yaxis.range[0]'], data['yaxis.range[1]']
        print(x_min, x_max)

    df = pd.read_sql(
        f"select * from emoji_umap where  A between {x_min:.3f} and {x_max:.37} and B between {y_min:.3f} and  {y_max:.3f}  order by RANDOM() limit 600;",
        con=e.con)
    fig = df.plot.scatter(x='A',
                          y='B',
                          text='emoji',
                          hover_data=['index'],
                          backend='plotly',
                          labels={
                              'A': '',
                              'B': ''
                          },
                          template='plotly_white')
    if data is not None and data.get('xaxis.range[0]'):
        fig.update_xaxes(range=[x_min, x_max])
        fig.update_yaxes(range=[y_min, y_max])
    fig.update_layout(font=dict(
        size=24,  # Set the font size here
    ))
    # fig.update_traces(textfont_size=14)
    return fig


@app.callback(
    Output("emoji-result", "children"),
    Input('my-graph', 'clickData'),
    State('font-size-slider', 'value'),
)
def custom_copy(click_data, fs):
    print(click_data)
    if click_data and click_data.get('points', []):
        first_point = click_data['points'][0]
        try:
            theemoji = first_point['customdata'][0]
        except KeyError:
            print('key error')
            theemoji = None
            raise PreventUpdate
        print(f"returning {theemoji}")
        return wrap_emoji(
            {
                'label': theemoji,
                'emoji': e.emoji_dict[theemoji]['emoji'],
                'text': 'the-clicked-emoji'
            }, fs)  # includes headers
    raise PreventUpdate


if __name__ == "__main__":
    app.run_server(debug=True)
