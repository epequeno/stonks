#![feature(proc_macro_hygiene, decl_macro)]
#[macro_use]
extern crate rocket;
use reqwest;
use rocket::State;

// define the env vars we're looking for once here as we'll reference
// them in several places later.
const SYMBOL_VAR_KEY: &'static str = "SYMBOL";
const NDAYS_VAR_KEY: &'static str = "NDAYS";
const API_TOKEN_KEY: &'static str = "APIKEY";

// define the upstream API we'll use to pull data from
const STOCK_API: &'static str = "https://www.alphavantage.co";

// primary application configuration object. We'll fill this in with
// data we get from environment variables once and pass it to rocket so
// responses don't have to lookup per request.
struct Config {
    symbol: String,
    ndays: usize,
    api_token: String,
}

fn make_url(api_token: &str, symbol: &str) -> String {
    format!(
        "{}/query?apikey={}&function=TIME_SERIES_DAILY_ADJUSTED&symbol={}",
        STOCK_API, api_token, symbol
    )
}

// https://stackoverflow.com/a/58234247


#[get("/")]
fn index(config: State<Config>) -> String {
    let url = make_url(&config.api_token, &config.symbol);
    if let Ok(res) = reqwest::blocking::get(&url) {
        "success".to_string()
    } else {
        "err :(".to_string()
    }
}

fn missing_env_var_exit(env_var_key: &str) {
    eprintln!(
        "environment variable '{}' not found; please set this environment variable to proceed.",
        env_var_key
    );
    std::process::exit(1)
}

// create a Config object which rocket can use to maintain application state
// by reading environment variables
fn make_config(symbol_key: &str, ndays_key: &str, api_token_key: &str) -> Config {
    let mut symbol = String::new();
    let mut ndays: usize = 0;
    let mut api_token = String::new();

    for (k, v) in std::env::vars() {
        if k == symbol_key {
            symbol = v.clone();
        }

        if k == ndays_key {
            ndays = v.clone().parse().unwrap_or(1);
        }

        if k == api_token_key {
            api_token = v.clone();
        }
    }

    // confirm we got the settings we need to proceed
    if symbol.is_empty() {
        missing_env_var_exit(SYMBOL_VAR_KEY);
    }

    if api_token.is_empty() {
        missing_env_var_exit(API_TOKEN_KEY);
    }

    Config {
        symbol,
        ndays,
        api_token,
    }
}

fn main() {
    let config = make_config(SYMBOL_VAR_KEY, NDAYS_VAR_KEY, API_TOKEN_KEY);

    rocket::ignite()
        .manage(config)
        .mount("/", routes![index])
        .launch();
}
